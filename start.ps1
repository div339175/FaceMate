$ErrorActionPreference = "Stop"
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectDir

if (!(Test-Path "venv")) {
    py -m venv venv
}

& .\venv\Scripts\python.exe -m pip install --upgrade pip
& .\venv\Scripts\python.exe -m pip install -r requirements.txt

if (!(Test-Path ".env") -and (Test-Path ".env.example")) {
    Copy-Item .env.example .env
}

& .\venv\Scripts\python.exe manage.py migrate
& .\venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
