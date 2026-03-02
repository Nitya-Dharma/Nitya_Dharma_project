# Virtual Environment Activation Script for Nitya Dharma Project
# Run this script to activate the virtual environment before running Django commands

Write-Host "Activating virtual environment..." -ForegroundColor Green

# Check if venv exists
if (Test-Path ".\venv\Scripts\Activate.ps1") {
    .\venv\Scripts\Activate.ps1
    Write-Host "Virtual environment activated!" -ForegroundColor Green
    Write-Host "You can now run: python manage.py runserver" -ForegroundColor Cyan
} else {
    Write-Host "Error: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    Write-Host "Virtual environment created and activated!" -ForegroundColor Green
}

















