"""
Serviço de conversão de documentos para PDF usando LibreOffice.
Suporta: DOCX, PPTX, ODT, ODP
"""
import os
import subprocess
import logging
from uuid import uuid4
from pathlib import Path

from fastapi import FastAPI, UploadFile, HTTPException, Depends, Security
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# API Key para autenticação
API_KEY = os.getenv("API_KEY", "")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
    """Verifica se a API key é válida."""
    if not API_KEY:
        # Se não houver API_KEY configurada, permite acesso (dev mode)
        logger.warning("API_KEY não configurada - acesso sem autenticação")
        return True
    
    if not api_key:
        raise HTTPException(status_code=401, detail="API key obrigatória")
    
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="API key inválida")
    
    return True


app = FastAPI(
    title="Convert to PDF Service",
    description="Converte documentos DOCX/PPTX para PDF usando LibreOffice",
    version="1.0.0"
)

# Formatos suportados
SUPPORTED_EXTENSIONS = [".docx", ".pptx", ".odt", ".odp", ".doc", ".ppt"]

# Timeout para conversão (2 minutos)
CONVERSION_TIMEOUT = 120


@app.get("/health")
async def health_check():
    """Health check do serviço."""
    return {"status": "healthy", "service": "convert-to-pdf-service"}


@app.post("/convert")
async def convert_to_pdf(file: UploadFile, _: bool = Depends(verify_api_key)):
    """
    Converte documento (DOCX, PPTX, etc.) para PDF.
    
    - Recebe arquivo via multipart/form-data
    - Detecta tipo automaticamente pela extensão
    - Retorna PDF convertido
    """
    if not file.filename:
        raise HTTPException(400, "Nome do arquivo é obrigatório")
    
    # Detectar extensão
    filename = file.filename
    ext = Path(filename).suffix.lower()
    
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            400, 
            f"Formato não suportado: {ext}. Suportados: {', '.join(SUPPORTED_EXTENSIONS)}"
        )
    
    logger.info(f"Iniciando conversão: {filename}")
    
    # Gerar identificador único para arquivos temporários
    temp_id = str(uuid4())
    temp_input = f"/tmp/{temp_id}{ext}"
    temp_pdf = f"/tmp/{temp_id}.pdf"
    
    try:
        # Salvar arquivo temporário
        content = await file.read()
        with open(temp_input, "wb") as f:
            f.write(content)
        
        logger.info(f"Arquivo salvo: {temp_input} ({len(content)} bytes)")
        
        # Converter com LibreOffice
        result = subprocess.run(
            [
                "libreoffice",
                "--headless",
                "--convert-to", "pdf",
                "--outdir", "/tmp",
                temp_input
            ],
            capture_output=True,
            timeout=CONVERSION_TIMEOUT
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.decode() if result.stderr else "Erro desconhecido"
            logger.error(f"Erro na conversão: {error_msg}")
            raise HTTPException(500, f"Erro na conversão: {error_msg}")
        
        if not os.path.exists(temp_pdf):
            logger.error(f"PDF não foi gerado: {temp_pdf}")
            raise HTTPException(500, "PDF não foi gerado")
        
        pdf_size = os.path.getsize(temp_pdf)
        logger.info(f"PDF gerado: {temp_pdf} ({pdf_size} bytes)")
        
        # Retornar PDF
        output_filename = Path(filename).stem + ".pdf"
        return FileResponse(
            temp_pdf,
            media_type="application/pdf",
            filename=output_filename,
            headers={
                "Content-Disposition": f'attachment; filename="{output_filename}"'
            }
        )
    
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout na conversão: {filename}")
        raise HTTPException(504, "Timeout na conversão. Arquivo muito grande?")
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        raise HTTPException(500, f"Erro interno: {str(e)}")
    
    finally:
        # Limpar arquivo de entrada (PDF é limpo após download pelo FastAPI)
        if os.path.exists(temp_input):
            try:
                os.remove(temp_input)
            except Exception:
                pass


@app.get("/")
async def root():
    """Página inicial com informações do serviço."""
    return {
        "service": "Convert to PDF Service",
        "version": "1.0.0",
        "endpoints": {
            "POST /convert": "Converte documento para PDF",
            "GET /health": "Health check"
        },
        "supported_formats": SUPPORTED_EXTENSIONS
    }
