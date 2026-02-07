# PocketBase – Backend Dottò

Backend unico del progetto: DB, Auth, API REST, Storage, Realtime.

## Primo avvio

1. **Avvia con Docker** (dalla root del progetto):
   ```bash
   docker-compose up -d pocketbase
   ```

2. **Crea il primo superuser** (obbligatorio al primo avvio):
   - Apri nel browser: http://localhost:8090/_/
   - Oppure da terminale:
     ```bash
     docker-compose exec pocketbase /usr/local/bin/pocketbase superuser upsert admin@dotto.bike TUAPASSWORD
     ```

3. **Collection**  
   Le collection `events`, `racks`, `operators`, `tokens` sono create automaticamente dalla migration in `pb_migrations/`.

## Endpoint

- **API**: http://localhost:8090/api/
- **Admin UI**: http://localhost:8090/_/
- **Health**: http://localhost:8090/api/health

## Directory

- `pb_migrations/` – migration JS (collection e schema)
- `pb_hooks/` – hook (validazione foto, decremento slot, Brevo)
- `pb_data/` – dati (SQLite + file), generato a runtime, non in git

## Versione

PocketBase **v0.36.2** (binario scaricato nel Dockerfile).
