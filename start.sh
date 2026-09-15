#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if [[ ! -d "venv" ]]; then
  python3 -m venv venv
fi

source "venv/bin/activate"
python -m pip install --upgrade pip
pip install -r requirements.txt

if [[ ! -f ".env" && -f ".env.example" ]]; then
  cp .env.example .env
fi

python manage.py migrate
python manage.py runserver 0.0.0.0:8000
