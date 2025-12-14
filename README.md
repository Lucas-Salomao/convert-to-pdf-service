# Convert to PDF Service

Serviço de conversão de documentos para PDF usando LibreOffice.

## Formatos Suportados

- DOCX → PDF (Microsoft Word)
- PPTX → PDF (Microsoft PowerPoint)
- ODT → PDF (LibreOffice Writer)
- ODP → PDF (LibreOffice Impress)

## Endpoints

### POST /convert

Converte um documento para PDF.

**Request:**
- `file`: Arquivo (multipart/form-data)

**Response:**
- PDF do documento

**Exemplo com curl:**
```bash
curl -X POST -F "file=@documento.docx" http://localhost:8080/convert -o documento.pdf
```

### GET /health

Health check do serviço.

## Executar Localmente

### Com Docker

```bash
docker build -t convert-to-pdf-service .
docker run -p 8080:8080 convert-to-pdf-service
```

### Sem Docker (requer LibreOffice instalado)

```bash
pip install -r requirements.txt
uvicorn app.main:app --port 8080 --reload
```

## Deploy no Cloud Run

```powershell
.\deploy.ps1
```
