# FastAPI Custom Connector for Power Platform

A production-ready FastAPI backend designed to be consumed as a **Custom Connector** in Power Platform. Demonstrates how to build, document, and deploy APIs that integrate seamlessly with Power Automate and Power Apps.

## Features

- **FastAPI backend** with 4 CRUD endpoints
- **Auto-generated Swagger/OpenAPI** spec compatible with Power Platform Custom Connectors
- **Pydantic models** with validation
- **JWT Authentication** ready for production
- **Docker** deployment ready
- **Custom Connector definition** included (importable `.swagger.json`)

## Architecture

```
Power Automate / Power Apps
          │
          ▼
  Custom Connector (Swagger)
          │
          ▼
    ┌─────────────┐
    │   FastAPI   │
    │   Backend   │
    ├─────────────┤
    │ /employees  │ GET, POST
    │ /employees/{id} │ GET, PUT, DELETE
    │ /departments│ GET
    │ /health     │ GET
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │  Database   │
    │  (SQLite /  │
    │  PostgreSQL)│
    └─────────────┘
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/employees` | List all employees (paginated, filterable) |
| `POST` | `/api/v1/employees` | Create a new employee |
| `GET` | `/api/v1/employees/{id}` | Get employee by ID |
| `PUT` | `/api/v1/employees/{id}` | Update employee |
| `DELETE` | `/api/v1/employees/{id}` | Delete employee |
| `GET` | `/api/v1/departments` | List all departments |
| `GET` | `/health` | Health check |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --port 8000

# View API docs
# http://localhost:8000/docs
```

## Importing into Power Platform

1. Go to **Power Automate** → **Data** → **Custom connectors**
2. Click **+ New custom connector** → **Import an OpenAPI file**
3. Upload `custom-connector/connector.swagger.json`
4. Configure authentication (API Key or OAuth 2.0)
5. Test the connector
6. Use in your flows!

## Tech Stack

- **Python 3.11+** / **FastAPI** / **Uvicorn**
- **Pydantic v2** for validation
- **SQLAlchemy** + **SQLite** (swappable to PostgreSQL)
- **Docker** for deployment
- **pytest** for testing

## License

MIT
