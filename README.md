# Blog-Website

A Django REST-based backend API for user management and education-related services.

---

## 🚀 Features

* Django REST Framework API
* Modular app structure
* Dockerized for deployment
* Separated core, apps, API, and test logic
* Pre-commit hook support

---

## 📦 Project Structure

```
Blog-Website/
├── docker-compose.yml          # Docker multi-service setup
├── Dockerfile                  # Docker image definition
├── LICENSE
├── manage.py                   # Django entry point
├── requirements.txt            # Project dependencies
├── .pre-commit-config.yaml     # Pre-commit hook definitions
├── README.md                   # Project setup guide (this file)
└── apps                        # Main source code directory, business logic and API
├
├── core/                       # Main Django settings, URLs, ASGI/WSGI

```

---

## ⚙️ Configuration

### 1. Clone the repository

```bash
git clone https://github.com/Khurshid2885/blog-website.git
cd blog-website
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

Create a `.env` file in the root (if required by your `settings.py`) with variables like:

```env
DEBUG=True
SECRET_KEY=your-secret-key
```

Or update `core/settings.py` directly.

---

## 🧼 Enable Pre-commit Hooks

To automatically format and lint your code before each commit:

### Install pre-commit

```bash
pip install pre-commit
```

### Install hooks

```bash
pre-commit install
```

### Run hooks manually (optional)

```bash
pre-commit run --all-files
```

Make sure `.pre-commit-config.yaml` is up to date with your desired hooks.

---

## 🐘 Setup Database (Optional PostgreSQL)

```bash
# Access PostgreSQL shell
sudo -u postgres psql

# Create DB and user
CREATE DATABASE blog_db;
CREATE USER db_user WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE blog_db TO db_user;
```

Then apply migrations:

```bash
python manage.py migrate
```

---

## 🔐 Create Superuser

```bash
python manage.py createsuperuser
```

---

## 🏃 Run the Server

```bash
python manage.py runserver
```

Visit: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

## 🐳 Docker Support

### Build and run with Docker Compose

```bash
docker-compose up --build
```

To stop:

```bash
docker-compose down
```

---

## ✅ Run Tests

```bash
pytest
```

Or:

```bash
python manage.py test
```

---

## 📄 License

This project is licensed under the terms of the `LICENSE` file.
