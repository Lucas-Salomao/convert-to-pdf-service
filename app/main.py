"""
Serviço de conversão de documentos para PDF usando LibreOffice.
Focado em fidelidade visual e isolamento de processos.
"""
import os
import subprocess
import logging
import shutil
import asyncio
from uuid import uuid4
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, UploadFile, HTTPException, Depends, Security, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader
from dotenv import load_dotenv

load_dotenv()

# Configuração de Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Configurações
API_KEY = os.getenv("API_KEY", "")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
CONVERSION_TIMEOUT = 120  # 2 minutos

# Executor para não bloquear o loop de eventos do FastAPI com subprocess
executor = ThreadPoolExecutor(max_workers=4)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if not API_KEY:
        logger.warning("WARN: API_KEY não configurada. Acesso liberado.")
        return True
    if not api_key or api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return True

app = FastAPI(title="High Fidelity PDF Converter", version="2.0.0")

SUPPORTED_EXTENSIONS = {".docx", ".pptx", ".odt", ".odp", ".doc", ".ppt", ".rtf", ".txt"}

def cleanup_temp_dir(path: Path):
    """Remove o diretório temporário após a resposta ser enviada."""
    try:
        shutil.rmtree(path, ignore_errors=True)
        logger.info(f"Diretório temporário removido: {path}")
    except Exception as e:
        logger.warning(f"Erro ao limpar temp {path}: {e}")

def run_libreoffice_conversion(input_path: str, output_dir: str, user_profile_dir: str):
    """
    Executa o LibreOffice em modo headless com perfil de usuário isolado.
    O perfil isolado (-env:UserInstallation) é crucial para concorrência e estabilidade.
    """
    # Filtro PDF com opções para preservar fidelidade do layout
    # UseLosslessCompression: evita perda de qualidade em imagens
    # ExportFormFields: mantém campos de formulário se houver
    pdf_filter = 'pdf:writer_pdf_Export:{"UseLosslessCompression":{"type":"boolean","value":"true"},"Quality":{"type":"long","value":"100"}}'
    
    command = [
        "libreoffice",
        "--headless",
        "--convert-to", pdf_filter,
        "--outdir", output_dir,
        # Define um diretório de configuração único para esta execução
        f"-env:UserInstallation=file://{user_profile_dir}",
        input_path
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        timeout=CONVERSION_TIMEOUT,
        env={**os.environ, "HOME": user_profile_dir} # Garante que LO use o home temporário
    )
    return result

@app.post("/convert")
async def convert_to_pdf(file: UploadFile, background_tasks: BackgroundTasks, _: bool = Depends(verify_api_key)):
    if not file.filename:
        raise HTTPException(400, "Arquivo sem nome")

    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(400, f"Formato não suportado. Use: {', '.join(SUPPORTED_EXTENSIONS)}")

    request_id = str(uuid4())
    base_tmp = Path("/tmp") / request_id
    
    # Estrutura de diretórios temporários isolados
    temp_input_dir = base_tmp / "input"
    temp_output_dir = base_tmp / "output"
    temp_profile_dir = base_tmp / "profile"
    
    temp_input_dir.mkdir(parents=True, exist_ok=True)
    temp_output_dir.mkdir(parents=True, exist_ok=True)
    temp_profile_dir.mkdir(parents=True, exist_ok=True)

    input_file_path = temp_input_dir / file.filename
    output_filename = Path(file.filename).stem + ".pdf"
    output_file_path = temp_output_dir / output_filename

    try:
        # Salvar arquivo recebido
        content = await file.read()
        with open(input_file_path, "wb") as f:
            f.write(content)

        logger.info(f"[{request_id}] Iniciando conversão: {file.filename}")

        # Executar conversão em thread separada para não travar a API (AsyncIO)
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            executor,
            run_libreoffice_conversion,
            str(input_file_path),
            str(temp_output_dir),
            str(temp_profile_dir)
        )

        if result.returncode != 0:
            error_msg = result.stderr.decode()
            logger.error(f"[{request_id}] Erro LibreOffice: {error_msg}")
            # Limpa imediatamente em caso de erro
            shutil.rmtree(base_tmp, ignore_errors=True)
            raise HTTPException(500, f"Falha na conversão: {error_msg}")

        if not output_file_path.exists():
            logger.error(f"[{request_id}] PDF não gerado no caminho esperado")
            # Limpa imediatamente em caso de erro
            shutil.rmtree(base_tmp, ignore_errors=True)
            raise HTTPException(500, "O arquivo PDF não foi gerado pelo conversor")

        # Agendar limpeza para DEPOIS que a resposta for enviada completamente
        background_tasks.add_task(cleanup_temp_dir, base_tmp)

        # Retornar arquivo
        return FileResponse(
            output_file_path,
            media_type="application/pdf",
            filename=output_filename
        )

    except subprocess.TimeoutExpired:
        logger.error(f"[{request_id}] Timeout na conversão")
        shutil.rmtree(base_tmp, ignore_errors=True)
        raise HTTPException(504, "O documento é muito complexo ou grande para o tempo limite")
    
    except HTTPException:
        # Re-raise HTTPExceptions sem modificação (já foram tratadas)
        raise
    
    except Exception as e:
        logger.exception(f"[{request_id}] Erro inesperado")
        shutil.rmtree(base_tmp, ignore_errors=True)
        raise HTTPException(500, str(e))

@app.get("/health")
async def health():
    return {"status": "ok", "mode": "headless-isolated"}