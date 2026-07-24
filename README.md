# RADIS Engineering Suite

RADIS is an engineering operations platform under active development. The current repository contains a Django REST backend for users, organizations, projects, assets, documents, locations, work orders, preventive maintenance, access control, and inventory.

## Stage 1 status

The foundation branch adds:

- a registered Inventory API under `/api/inventory/`
- a health endpoint at `/api/health/`
- JWT login and refresh endpoints
- a complete backend dependency list
- environment-variable examples
- automated Django checks and tests in GitHub Actions

## Local backend setup

### Requirements

- Python 3.13
- Git

### Windows PowerShell

```powershell
git clone https://github.com/mkorom1375-droid/radis-engineering-suite-4.git
cd radis-engineering-suite-4
git checkout develop/foundation-stage-1

cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Linux or macOS

```bash
git clone https://github.com/mkorom1375-droid/radis-engineering-suite-4.git
cd radis-engineering-suite-4
git checkout develop/foundation-stage-1

cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Verification

Run the following commands from the `backend` directory:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Then open:

- Health check: `http://127.0.0.1:8000/api/health/`
- Admin: `http://127.0.0.1:8000/admin/`
- Inventory warehouses: `http://127.0.0.1:8000/api/inventory/warehouses/`

Most business APIs require authentication. Obtain a JWT access token from:

```text
POST /api/auth/login/
```

Refresh it through:

```text
POST /api/auth/refresh/
```

## Security

Never commit `.env`, database files, API keys, passwords, or access tokens. Use `backend/.env.example` as the configuration template.
