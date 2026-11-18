#!/bin/bash
# Empaqueta la app y crea o actualiza toda la infraestructura en AWS.
# Acepta opciones de terraform apply, por ejemplo: terraform/deploy.sh -var deezer_url=https://api.deezer.invalid
set -e
cd "$(dirname "$0")/.."
[ -d .venv ] || python3 -m venv .venv

# 1. Empaquetar main.py, static/ y las librerías en su versión para Linux, que es donde corre Lambda
rm -rf build dist && mkdir dist
.venv/bin/pip install --quiet --no-cache-dir --disable-pip-version-check --target build \
  --platform manylinux2014_x86_64 --python-version 3.14 --only-binary=:all: fastapi mangum httpx
cp -r main.py static build/
find build -name __pycache__ -prune -exec rm -rf {} +
find build -exec touch -t 202601010000 {} +  # fechas fijas: mismo código, mismo zip
(cd build && find . -type f | sort | zip -qX ../dist/onda-lambda.zip -@)
rm -rf build
du -h dist/onda-lambda.zip

# 2. Crear o actualizar la infraestructura
terraform -chdir=terraform init -input=false
terraform -chdir=terraform apply "$@"
