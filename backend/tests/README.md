# Test backend

Suite di **unit/integration test** organizzati per modulo.

## Moduli testati

- **`test_pocketbase_collections.py`**: Health API, collections (events, tokens, racks, operators), filtri base
- **`test_pocketbase_hooks.py`**: Hook JavaScript PocketBase (validazione foto token fisici)
- **`test_backend_basic.py`**: Import base del package FastAPI (per coverage)

## Requisiti

- **PocketBase in esecuzione** su `http://localhost:8090` (o `POCKETBASE_URL`):
  ```bash
  make up-pocketbase
  # oppure: make up
  ```
- **Python venv** con dipendenze dev: `make venv` (dalla root del progetto).

## Esecuzione

Dalla **root del progetto**:

```bash
make test          # test backend + frontend
make test-backend  # solo pytest (tutti i moduli)
make test-coverage # pytest con report coverage (term + html in backend/htmlcov)
```

Solo backend:

```bash
. .venv/bin/activate && cd backend && python -m pytest tests -v
```

## Test PocketBase Collections

Test sempre eseguiti se PocketBase è up:
- Health API (`/api/health`)
- Presenza e risposta delle collection: `events`, `tokens`, `racks`, `operators`
- Filtro eventi attivi

## Test PocketBase Hooks

I test che creano/aggiornano token richiedono un **superuser** PocketBase. Puoi fornire le credenziali in due modi:

**Nota:** Il decremento slot non viene testato qui perché non può essere implementato negli hook PocketBase (causa 400, anche usando gli hook di modello suggeriti per modifiche cross-collection). Il decremento slot verrà testato quando implementiamo l'endpoint FastAPI di check-in.

1. **File `.env`** alla root del progetto (consigliato):
   ```bash
   PB_ADMIN_EMAIL=admin@example.com
   PB_ADMIN_PASSWORD=tua_password
   ```
   I test caricano automaticamente il `.env` e useranno queste variabili.

2. **Variabili d'ambiente** in shell:
   ```bash
   export PB_ADMIN_EMAIL=admin@example.com
   export PB_ADMIN_PASSWORD=tua_password
   make test-backend
   ```

Senza credenziali valide, i test degli hook vengono **skippati**.

È necessario almeno **un evento attivo** (creabile dalla Admin UI) per i test degli hook.

### 400 "Failed to create record" con `data` vuoto

Se i test degli hook restituiscono 400 con messaggio "Failed to create record." e `data: {}`:

1. Verifica che il **superuser** esista (Admin UI o `pocketbase superuser upsert`) e che `PB_ADMIN_EMAIL` / `PB_ADMIN_PASSWORD` nel `.env` siano corretti.
2. Verifica che esista **almeno un evento** con `is_active = true` (e, per i test slot, `slots_available >= 1`).
3. Controlla i log di PocketBase: `docker-compose logs pocketbase` (eventuali errori degli hook o di validazione compaiono lì).
4. Prova a creare un token **a mano dalla Admin UI** (stessi campi: event, email, token_code, token_type, status, newsletter_opt_in, whatsapp_sent) per vedere eventuali messaggi di errore espliciti.

## Coverage

- `make test-coverage` genera il report in terminale e in `backend/htmlcov/`.
- I test attuali esercitano l'API PocketBase (HTTP), non il modulo `app/` FastAPI, quindi la coverage del codice `app/` è bassa; aggiungendo test per il backend FastAPI la coverage aumenterà.
