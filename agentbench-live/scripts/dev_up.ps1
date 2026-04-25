# PowerShell helper — start the FastAPI backend + Vite dev server side-by-side.
# Run from D:\Redhat Hackathon\agentbench-live

$ErrorActionPreference = "Stop"

$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

# Backend — uses the venv's python
$backend = Start-Process -FilePath "$root\.venv\Scripts\python.exe" `
  -ArgumentList "-m","uvicorn","api_server.main:app","--reload","--port","8000" `
  -PassThru -NoNewWindow

# Frontend — Vite dev server
$frontend = Start-Process -FilePath "npm" -ArgumentList "run","dev" `
  -WorkingDirectory "$root\dashboard" -PassThru -NoNewWindow

Write-Host "API:       http://localhost:8000"
Write-Host "Dashboard: http://localhost:5173"
Write-Host "Press Ctrl+C to stop both processes."

try {
  Wait-Process -Id $backend.Id, $frontend.Id
} finally {
  Stop-Process -Id $backend.Id  -ErrorAction SilentlyContinue
  Stop-Process -Id $frontend.Id -ErrorAction SilentlyContinue
}
