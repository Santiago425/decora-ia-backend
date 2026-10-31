<div align="center">

# Habita · Backend

**API REST de Habita: diseño de interiores con inteligencia artificial y modelado 3D.**

Proyecto final de **Patrones de Diseño**

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.162-009688?logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2-D71F00)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)

</div>

## ¿En qué consiste?

**Habita** permite tomar o subir una foto de un espacio, elegir un estilo y ver cómo quedaría rediseñado por la IA, armar el espacio en un editor 3D con muebles del catálogo, calcular un presupuesto y guardar proyectos. **Lumi**, la asistente, guía al usuario por voz o texto.

Este repositorio es el **backend**: API REST con FastAPI, base de datos PostgreSQL y conexión con la IA (Google Gemini, intercambiable desde el `.env`).

| Componente | Repositorio | Producción |
|---|---|---|
| Frontend | [decora-ia-frontend](https://github.com/Santiago425/decora-ia-frontend) | https://decora-ia-frontend.vercel.app |
| Backend | [decora-ia-backend](https://github.com/Santiago425/decora-ia-backend) | https://decora-ia-backend.onrender.com/api/v1/hello |
| Documentación de la API | Swagger UI | https://decora-ia-backend.onrender.com/api/v1/docs |

## Arquitectura por capas

```mermaid
flowchart LR
    R[routers<br/>endpoints] --> S[services<br/>lógica]
    S --> RP[repositories<br/>datos]
    RP --> M[models<br/>ORM]
    M --> DB[(PostgreSQL)]
    SC[schemas<br/>Pydantic] -.entrada / salida.- R
    D[dependencies<br/>Depends] -.inyecta.- R
```

Los routers nunca tocan la base de datos: reciben los servicios por **inyección de dependencias** (`Depends` de FastAPI) y los servicios trabajan solo con repositorios.

## Patrones aplicados

| Patrón | Tipo | Dónde | Problema que resuelve |
|---|---|---|---|
| **Singleton** | Creacional | [`app/core/settings.py`](app/core/settings.py) | La configuración del `.env` se lee una sola vez y se comparte en toda la app. |
| **Singleton** | Creacional | [`app/patterns/singleton.py`](app/patterns/singleton.py), [`app/core/database.py`](app/core/database.py) | Una sola conexión (motor y pool) a la base de datos por proceso. |
| **Repository** | Arquitectura | [`app/repositories/`](app/repositories) | Los servicios piden y guardan entidades sin escribir SQL. |
| **Inyección de dependencias** | Arquitectura | [`app/dependencies.py`](app/dependencies.py) | Cada endpoint recibe sus servicios ya armados; en las pruebas se pueden reemplazar. |

Los demás patrones (Factory Method, Abstract Factory, Builder, Prototype, Adapter, Facade, Decorator, Composite, Proxy, Strategy, Command, Memento, Observer, State, Chain of Responsibility y Template Method) se suman en las siguientes fases.

## Base de datos

Todas las opciones de la app (estilos, tipos de habitación, categorías y catálogo de muebles, materiales y paletas) viven en la base de datos: para agregar un estilo nuevo basta con insertarlo y aparece en la app sin tocar código.

```mermaid
erDiagram
    users ||--o{ projects : owns
    users ||--o{ chat_messages : writes
    room_types ||--o{ projects : classifies
    design_styles ||--o{ projects : styles
    design_styles ||--o{ color_palettes : has
    design_styles }o--o{ materials : style_materials
    projects ||--o{ redesigns : has
    projects ||--o{ scene_versions : saves
    design_styles ||--o{ redesigns : uses
    furniture_categories ||--o{ furniture_items : groups

    users { uuid id PK
        string full_name
        string email
        string password_hash
        string role
        bool is_active }
    projects { uuid id PK
        uuid user_id FK
        int room_type_id FK
        int style_id FK
        string name
        string status
        decimal estimated_budget
        json scene }
    redesigns { uuid id PK
        uuid project_id FK
        string original_image_url
        string result_image_url
        json suggestions
        string status }
    furniture_items { int id PK
        int category_id FK
        string name
        decimal price
        float width
        float depth
        float height }
```

Las tablas se crean con migraciones de **Alembic** ([`migrations/`](migrations)) que se ejecutan solas al arrancar el contenedor.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/v1/hello` | Hello World |
| `GET` | `/api/v1/health` | Estado de la API y de la base de datos |
| `POST` | `/api/v1/auth/register` | Crea una cuenta de usuario |
| `POST` | `/api/v1/auth/login` | Inicia sesión como usuario o administrador (`role`) |
| `GET` | `/api/v1/auth/me` | Datos de la sesión 🔐 |
| `GET` | `/api/v1/catalog/styles` | Estilos con sus paletas y materiales |
| `GET` | `/api/v1/catalog/room-types` | Tipos de habitación |
| `GET` | `/api/v1/catalog/furniture-categories` | Categorías de muebles |
| `GET` | `/api/v1/catalog/furniture?category=` | Catálogo de muebles |
| `GET` | `/api/v1/catalog/materials?surface=` | Materiales de pared, piso y muebles |
| `GET` | `/api/v1/catalog/palettes` | Paletas de colores |

🔐 = requiere `Authorization: Bearer <token>`.

## Cuentas de prueba

| Rol | Correo | Contraseña |
|---|---|---|
| Usuario | `usuario@habita.app` | `Habita2026` |
| Administrador | `admin@habita.app` | `Habita2026` |

Las crea [`app/seed.py`](app/seed.py) junto con el catálogo ([`app/seed_data/catalog.json`](app/seed_data/catalog.json)). Correos, nombres y contraseña salen del `.env` (`DEMO_*`).

## Seguridad

- Contraseñas con **bcrypt**; nunca se guardan ni se devuelven en texto plano.
- Sesiones con **JWT** firmado y con expiración (`JWT_EXPIRE_MINUTES`).
- Un usuario normal no puede entrar por el acceso de administrador, y el registro solo crea usuarios normales.
- Mismo mensaje y mismo tiempo de respuesta para correo inexistente o contraseña incorrecta.
- Límite de intentos por IP en login y registro (`LOGIN_RATE_LIMIT`, `REGISTER_RATE_LIMIT`).
- CORS restringido a `CORS_ORIGINS` y cabeceras de seguridad en cada respuesta.
- Contenedor sin usuario root y secretos solo en variables de entorno.

## Ejecutar en local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload      # http://localhost:8000/api/v1/docs
pytest
```

Con Docker:

```bash
docker build -t habita-backend .
docker run -p 8000:8000 --env-file .env habita-backend
```

## Variables de entorno

Todas están en [`.env.example`](.env.example) con comentarios y se leen en un solo lugar: [`app/core/settings.py`](app/core/settings.py).

| Variable | Para qué |
|---|---|
| `APP_NAME`, `APP_ENV`, `API_PREFIX`, `PORT` | Datos generales de la aplicación |
| `DATABASE_URL`, `DATABASE_ECHO` | Conexión a la base de datos (SQLite en local, PostgreSQL en producción) |
| `CORS_ORIGINS` | Orígenes del frontend permitidos |
| `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRE_MINUTES` | Firma y duración de las sesiones |
| `LOGIN_RATE_LIMIT`, `REGISTER_RATE_LIMIT` | Límite de intentos |
| `SEED_ON_STARTUP` | Cargar catálogo y cuentas de prueba al arrancar |
| `DEMO_PASSWORD`, `DEMO_USER_*`, `DEMO_ADMIN_*` | Cuentas de prueba |

## Estructura

```
app/
├── core/            settings (Singleton), database, security, rate limit
├── models/          Modelos ORM (SQLAlchemy)
├── schemas/         Entrada y salida (Pydantic)
├── repositories/    Acceso a datos (Repository)
├── services/        Lógica de negocio
├── patterns/        Implementaciones de los patrones de diseño
├── routers/         Endpoints REST
├── seed_data/       Catálogo inicial en JSON
├── dependencies.py  Inyección de dependencias
├── seed.py          Script de semilla
└── main.py
migrations/          Migraciones de Alembic
tests/               Pruebas con pytest
```

## Equipo

| Integrante | GitHub |
|---|---|
| Santiago Campoverde | [@Santiago425](https://github.com/Santiago425) |
| Never Melo | [@neber18](https://github.com/neber18) |
