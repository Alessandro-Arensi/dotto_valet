# Test backend

Suite di **unit/integration test** per il backend FastAPI.

## File di test attuali

- **`test_backend_basic.py`**: Import base del package FastAPI (per coverage).
- **`test_email_service.py`**: Test del servizio email (Brevo).

## Requisiti

- **Python venv** con dipendenze dev: `make venv` (dalla root del progetto).

## Esecuzione

Dalla **root del progetto**:

```bash
make test          # test backend + frontend
make test-backend  # solo pytest (tutti i moduli backend)
make test-coverage # pytest con report coverage (term + html in backend/htmlcov)
```

Solo backend:

```bash
. .venv/bin/activate && cd backend && python -m pytest tests -v
```

## Coverage

- `make test-coverage` genera il report in terminale e in `backend/htmlcov/`.
- I test attuali coprono solo una parte del backend FastAPI; aggiungendo test per gli endpoint (es. prenotazione, check-in, token) la coverage aumenterà.
