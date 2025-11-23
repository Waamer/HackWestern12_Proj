# Start Development - Backend and Frontend
# This script starts both the Flask backend and Vite frontend

Write-Host "Starting Emotion Chat Application..." -ForegroundColor Green
Write-Host ""

# Get the script directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Start Backend in a new window
Write-Host "Starting Backend (Flask)..." -ForegroundColor Cyan
$backendCmd = "Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force; & '.\.venv\Scripts\Activate.ps1'; cd backend; python app.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

# Wait a moment for backend to initialize
Start-Sleep -Seconds 2

# Start Frontend in a new window
Write-Host "Starting Frontend (Vite)..." -ForegroundColor Cyan
$frontendCmd = "cd '$scriptPath\frontend'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Write-Host ""
Write-Host "✅ Both servers are starting!" -ForegroundColor Green
Write-Host ""
Write-Host "Backend will be at: http://localhost:5000" -ForegroundColor Yellow
Write-Host "Frontend will be at: http://localhost:5173" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Ctrl+C in each window to stop the servers" -ForegroundColor Gray
