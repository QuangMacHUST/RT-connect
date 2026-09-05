param(
  [switch]$WithContainers
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$apiPython = "$root\apps\api\.venv\Scripts\python.exe"
if (-not (Test-Path $apiPython)) { $apiPython = 'python' }
$dockerCommand = (Get-Command docker -ErrorAction SilentlyContinue).Source
if (-not $dockerCommand) {
  $userDockerCommand = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe"
  if (Test-Path $userDockerCommand) { $dockerCommand = $userDockerCommand }
}
if ($dockerCommand) {
  $dockerBin = Split-Path -Parent $dockerCommand
  if (($env:Path -split ';') -notcontains $dockerBin) { $env:Path = "$dockerBin;$env:Path" }
}

Push-Location "$root\apps\api"
& $apiPython -m pytest
& $apiPython -m ruff check src tests
& $apiPython -m mypy src
& $apiPython -m alembic upgrade head --sql | Out-Null
Pop-Location

Push-Location "$root\apps\web"
npm run lint
npm run typecheck
npm run test
npm run build
Pop-Location

if ($WithContainers) {
  if (-not $dockerCommand) { throw 'Docker CLI is required for -WithContainers.' }
  $composeArguments = @('compose', '-f', "$root\docker-compose.yml")
  try {
    & $dockerCommand @composeArguments up --build --wait
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose did not become healthy.' }
    & $dockerCommand @composeArguments exec -T api alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'Alembic migration failed inside the API container.' }
    & $dockerCommand @composeArguments exec -T api python -m rt_connect_api.cli seed-synthetic
    if ($LASTEXITCODE -ne 0) { throw 'Synthetic seed failed inside the API container.' }
    $seedCount = & $dockerCommand @composeArguments exec -T postgres psql -U rt_connect -d rt_connect -tAc 'SELECT count(*) FROM machines;'
    if ($LASTEXITCODE -ne 0 -or [int]$seedCount -lt 1) { throw 'Synthetic machine seed was not persisted.' }
    $health = Invoke-RestMethod 'http://localhost:8000/api/v1/health'
    if ($health.status -ne 'ok') { throw 'API health did not return ok.' }
    $readiness = Invoke-RestMethod 'http://localhost:8000/api/v1/ready'
    if ($readiness.status -ne 'ready') { throw 'API readiness did not return ready.' }
    Invoke-WebRequest 'http://localhost:5173/health' -UseBasicParsing | Out-Null
  }
  finally {
    & $dockerCommand @composeArguments down -v
  }
}
