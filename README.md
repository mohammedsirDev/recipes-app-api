# Recipes App API

A production-ready REST API built with Django REST Framework, following **Test-Driven Development (TDD)** methodology throughout.

## Features

- User authentication with token-based auth
- Create, update, and delete recipes with tags and ingredients
- Image upload support
- Filter and search recipes by tags and ingredients
- Fully Dockerised development and production environments
- Automated CI with GitHub Actions

## Tech Stack

- **Backend:** Python, Django, Django REST Framework
- **Database:** PostgreSQL
- **Containerisation:** Docker, Docker Compose
- **Testing:** pytest, TDD methodology
- **CI/CD:** GitHub Actions
- **Proxy:** Nginx

## Getting Started

```bash
git clone https://github.com/mohammedsirDev/recipes-app-api.git
cd recipes-app-api
cp .env.sample .env
docker-compose up
```

API will be available at `http://localhost:8000/api/docs`

## Running Tests

```bash
docker-compose run --rm app sh -c "python manage.py test"
```
