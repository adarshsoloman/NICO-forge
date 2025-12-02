# NICO-Forge Setup Script
# Quick setup for Windows using uv

Write-Host "🔥 NICO-Forge Setup" -ForegroundColor Cyan
Write-Host "===================" -ForegroundColor Cyan
Write-Host ""

# Check if uv is installed
Write-Host "Checking for uv..." -ForegroundColor Yellow
if (!(Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "❌ uv not found. Please install uv first:" -ForegroundColor Red
    Write-Host "   pip install uv" -ForegroundColor White
    exit 1
}
Write-Host "✓ uv found" -ForegroundColor Green

# Create virtual environment
Write-Host "`nCreating virtual environment..." -ForegroundColor Yellow
uv venv
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to create virtual environment" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Virtual environment created" -ForegroundColor Green

# Activate virtual environment
Write-Host "`nActivating virtual environment..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "`nInstalling dependencies..." -ForegroundColor Yellow
uv pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Dependencies installed" -ForegroundColor Green

# Create .env from template
Write-Host "`nSetting up environment file..." -ForegroundColor Yellow
if (!(Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "✓ Created .env file" -ForegroundColor Green
    Write-Host "⚠️  IMPORTANT: Edit .env and add your OPENROUTER_API_KEY" -ForegroundColor Yellow
} else {
    Write-Host "✓ .env file already exists" -ForegroundColor Green
}

# Create test data
Write-Host "`nCreating test data..." -ForegroundColor Yellow
python create_test_data.py
Write-Host "✓ Test data created" -ForegroundColor Green

Write-Host "`n" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green
Write-Host "✓ Setup complete!" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Edit .env and add your OpenRouter API key" -ForegroundColor White
Write-Host "2. Run the pipeline:" -ForegroundColor White
Write-Host "   python main.py test_data/sample_healthcare_en.txt" -ForegroundColor Yellow
Write-Host ""
