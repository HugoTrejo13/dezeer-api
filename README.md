# Onda

Reproductor de música web hecho con la API pública de Deezer y desplegado en AWS Lambda.

## 1. Qué es

Una página para buscar canciones y artistas, escuchar vistas previas de 30 segundos y armar tus propias playlists.

Hecha con FastAPI (Python) en el backend y Tailwind con Alpine.js en la interfaz.

## 2. Cómo funciona en AWS

```
Navegador ──► Function URL ──► AWS Lambda (main.py) ──► API de Deezer
```

La app corre en **AWS Lambda**: solo se ejecuta cuando alguien entra y se accede con un link público (**Function URL**). Toda la infraestructura está escrita con **Terraform** en `terraform/main.tf`, así que se crea y actualiza con comandos en lugar de usar la consola de AWS.

```bash
terraform/build.sh                        # empaqueta el código en docs/onda-lambda.zip
terraform -chdir=terraform apply          # lo sube y crea todo en AWS
```

## 3. Cómo tenerlo en tu computadora

Algunas carpetas no están en el repositorio porque se generan solas o tienen datos de la cuenta de AWS: `.venv/`, `terraform/.terraform/` y `terraform.tfstate`. Estos pasos las crean de nuevo.

**Requisitos:** Git, Python 3.12 o superior y `zip`. Para desplegar también necesitas [Terraform](https://developer.hashicorp.com/terraform/install), [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) y una cuenta de AWS. Los comandos son para macOS o Linux; en Windows usa WSL.

### Correrlo en local

```bash
git clone https://github.com/HugoTrejo13/dezeer-api.git
cd dezeer-api

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

.venv/bin/uvicorn main:app --reload
```

Abre `http://localhost:8000` para la app y `http://localhost:8000/docs` para los endpoints. Detén el servidor con `Ctrl + C`.

### Desplegarlo en tu propia cuenta de AWS

Antes haz los pasos de "Correrlo en local": `build.sh` usa el `.venv` que se crea ahí.

```bash
aws login                                 # o: aws configure
terraform -chdir=terraform init           # descarga el proveedor de AWS
terraform/build.sh                        # genera el zip
terraform -chdir=terraform apply          # escribe "yes" para confirmar
terraform -chdir=terraform output url     # tu link
```

Como `terraform.tfstate` no está en el repositorio, Terraform crea recursos nuevos en tu cuenta. El estado se guarda en tu computadora, en `terraform/terraform.tfstate`.

### Actualizar después de cambiar el código

```bash
terraform/build.sh && terraform -chdir=terraform apply
```

### Borrar todo de AWS

```bash
terraform -chdir=terraform destroy
```
