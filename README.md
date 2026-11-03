# shopdesk

Small order-management API (catalog, orders, uploads, account preferences) built with Flask and SQLite.

## Run the tests

    python -m venv venv && . venv/bin/activate
    pip install -r requirements.txt -r requirements-dev.txt
    pytest

## Endpoints

- `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`
- `POST /auth/reset/request`, `POST /auth/reset/confirm`, `GET /auth/continue`
- `GET /catalog/search`, `GET /catalog/products/<id>`, `GET /catalog/products/<id>/card`, `POST /catalog/products`
- `POST /orders`, `GET /orders/<id>`, `GET /orders/user/<id>`, `GET /orders/export.csv`
- `POST /files/upload`, `GET /files/download`
- `GET /tools/ping`, `POST /tools/calc`, `GET /tools/fetch`, `POST /tools/import-config`
- `GET|PUT /account/prefs`, `GET /account/users`
