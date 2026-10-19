# ShopSphere — Django E-commerce Store

ShopSphere is a learning project that demonstrates a small e-commerce site built with Django. It includes a product catalogue, customer accounts, private shopping carts, and a simulated order flow.

> **Demo checkout only:** checkout records an order for demonstration. No real payments are processed, and the site does not collect payment card details.

## Features

- Browse the product catalogue, with product information and locally stored product images.
- Open an individual product detail page.
- Register, log in, and log out using Django's built-in authentication.
- Add products to a database-backed cart, change quantities, and remove items. Each signed-in user has a private cart.
- Review delivery details and submit the simulated checkout. The server calculates order totals from catalogue prices.
- View an order confirmation and private order history. Order items retain product-name and unit-price snapshots.
- Manage products and orders through Django admin.
- Responsive pages with the existing purple ShopSphere design.

## Technology

- Python 3.14
- Django 6.0.9
- SQLite for local development
- Django templates, HTML, CSS, and JavaScript

## Run locally on Windows

Open PowerShell and move into the project folder:

```powershell
Set-Location "$env:USERPROFILE\Documents\CodeAlpha_EcommerceStore"
```

Create a virtual environment and install the pinned Django dependency:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The commands below call the virtual-environment Python directly, so activating the environment in PowerShell is optional:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Open <http://127.0.0.1:8000/> in a browser. To create an administrator account for the Django admin, run this in another PowerShell window from the project folder:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Then visit <http://127.0.0.1:8000/admin/>.

## Check the project

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate --check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test
```

The sample catalogue is added by the existing data migration when migrations are applied to a new database.

## Local data and deployment note

The local SQLite database (`db.sqlite3`) and generated development secret (`.secret_key`) are private local files and are excluded from Git. Applying migrations to a fresh database creates the sample products. Do not publish a real `.env` file, secret key, or database containing personal data.

The current Django settings are for local development (`DEBUG=True` and an empty `ALLOWED_HOSTS`). Configure and review production security settings before deploying this project to a public server. Publishing the source repository does not make the application production-ready.
