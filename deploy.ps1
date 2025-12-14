# Script de deploy para o Cloud Run
# Serviço de conversão PDF com LibreOffice

$ErrorActionPreference = "Stop"

# Configurações
$PROJECT_ID = "gerador-de-apostila"
$SERVICE_NAME = "convert-to-pdf-service"
$REGION = "us-east1"
$IMAGE_TAG = "gcr.io/$PROJECT_ID/$SERVICE_NAME"

Write-Host "=== Deploy do Convert to PDF Service ===" -ForegroundColor Cyan
Write-Host ""

# Verificar autenticação
Write-Host "Verificando autenticação..." -ForegroundColor Yellow
gcloud auth print-identity-token | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Erro: Não autenticado. Execute 'gcloud auth login'" -ForegroundColor Red
    exit 1
}

# Definir projeto
Write-Host "Usando projeto: $PROJECT_ID" -ForegroundColor Yellow
gcloud config set project $PROJECT_ID

# Habilitar APIs necessárias
Write-Host "Habilitando APIs necessárias..." -ForegroundColor Yellow
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com

# Build e push da imagem
Write-Host "Construindo imagem Docker (pode demorar ~5min na primeira vez)..." -ForegroundColor Yellow
gcloud builds submit --tag $IMAGE_TAG .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Erro no build da imagem" -ForegroundColor Red
    exit 1
}

# Deploy no Cloud Run
Write-Host "Fazendo deploy no Cloud Run..." -ForegroundColor Yellow
gcloud run deploy $SERVICE_NAME `
    --image $IMAGE_TAG `
    --platform managed `
    --region $REGION `
    --memory 1Gi `
    --cpu 1 `
    --timeout 300 `
    --concurrency 10 `
    --min-instances 0 `
    --max-instances 5 `
    --allow-unauthenticated `
    --port 8080

if ($LASTEXITCODE -ne 0) {
    Write-Host "Erro no deploy" -ForegroundColor Red
    exit 1
}

# Obter URL do serviço
$SERVICE_URL = gcloud run services describe $SERVICE_NAME --region $REGION --format "value(status.url)"

Write-Host ""
Write-Host "=== Deploy concluído com sucesso! ===" -ForegroundColor Green
Write-Host "URL do serviço: $SERVICE_URL" -ForegroundColor Cyan
Write-Host ""
Write-Host "Teste com:" -ForegroundColor Yellow
Write-Host "curl -X POST -F 'file=@documento.docx' $SERVICE_URL/convert -o documento.pdf"
