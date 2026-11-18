set -e
cd "$(dirname "$0")/.."
rm -rf build docs/onda-lambda.zip
.venv/bin/pip install --quiet --no-cache-dir --disable-pip-version-check --target build \
  --platform manylinux2014_x86_64 --python-version 3.14 --only-binary=:all: fastapi mangum httpx
cp -r main.py static build/
(cd build && zip -qr ../docs/onda-lambda.zip . -x '*__pycache__*')
rm -rf build
du -h docs/onda-lambda.zip


