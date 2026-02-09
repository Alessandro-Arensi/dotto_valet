# Verifiche Step 2 – Hook PocketBase

Esegui queste verifiche dopo aver completato lo **Step 2** (hook in `pb_hooks/`: validazione foto token fisici).

**Nota:** Il decremento `slots_available` su evento in check-in **non** viene gestito negli hook PocketBase (causa problemi di transazione), ma sarà implementato nel backend FastAPI quando viene chiamato l'endpoint di check-in.

**Prerequisito:** Step 1 completato (PocketBase avviato, collections create, almeno un evento di test con `slots_available` > 0).

Se hai appena aggiunto o modificato file in `pb_hooks/`, riavvia PocketBase per caricare gli hook: `make down && make up` oppure `docker-compose restart pocketbase`.

---

## 1. Hook caricati

```bash
make logs-pocketbase
```

- **Verifica:** all’avvio non compare errore di sintassi o `Failed to load hooks`; il server parte normalmente (`Server started at http://0.0.0.0:8090`).

---

## 2. Validazione foto – token fisico senza foto (create)

Creare un token **fisico** senza allegare foto deve essere rifiutato con 400.

- **Da Admin UI:** in **tokens** crea un record con `token_type = physical`, **senza** caricare un file in `photo`. Salva.
- **Verifica:** messaggio di errore tipo “Foto bici obbligatoria per token fisici” (o simile) e il record non viene creato.

Oppure via API (se hai auth admin o createRule pubblica):

```bash
# Esempio: crea token physical senza photo (deve fallire con 400)
curl -s -X POST "http://localhost:8090/api/collections/tokens/records" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "EVENT_ID",
    "email": "test@example.com",
    "token_code": "DOT-TEST",
    "token_type": "physical",
    "status": "pending",
    "newsletter_opt_in": false,
    "whatsapp_sent": false
  }'
```

- **Verifica:** risposta HTTP 400 e messaggio che indica foto obbligatoria per token fisici.

---

## 3. Token digitale senza foto – consentito

- Crea un token con `token_type = digital`, **senza** foto.
- **Verifica:** il record viene creato senza errore.

---

## 4. Decremento slot – creazione con `status = checked_in`

**NOTA:** Modificare altri record (eventi) dagli hook PocketBase causa problemi di transazione.  
Il decremento slot verrà gestito nel **backend FastAPI** quando viene chiamato l’endpoint di check-in.

Per ora, verifica solo che:
- Puoi creare un token con `status = checked_in` senza errori.
- Il token viene creato correttamente.

Il decremento automatico degli slot sarà implementato nel backend FastAPI.

---

## 5. Decremento slot – update da `pending` a `checked_in`

**NOTA:** Come sopra, il decremento slot tramite hook causa problemi di transazione.  
Verifica solo che:
- Puoi aggiornare un token da `pending` a `checked_in` senza errori.
- Il token viene aggiornato correttamente.

Il decremento automatico degli slot sarà implementato nel backend FastAPI.

---

## 6. (Opzionale) Token fisico con foto – create e check-in

- Crea un token con `token_type = physical` **con** un file caricato in `photo`.
- **Verifica:** il record viene creato.
- Se lo crei già con `status = checked_in`, verifica anche che `slots_available` dell’evento diminuisca di 1.

---

## Riepilogo checklist Step 2

| # | Verifica | Azione |
|---|----------|--------|
| 1 | Hook caricati senza errori | `make logs-pocketbase` |
| 2 | Token physical senza foto rifiutato (create) | Creare token physical senza photo → 400 + messaggio |
| 3 | Token digital senza foto consentito | Creare token digital senza photo → OK |
| 4 | Creazione token con status checked_in (decremento slot gestito nel backend) | Creare token checked_in → verifica creazione OK |
| 5 | Update pending → checked_in (decremento slot gestito nel backend) | Update token → verifica update OK |
| 6 | (Opzionale) Token physical con foto creato e slot decrementato | Creare con photo, eventualmente checked_in |

Se tutte le verifiche passano, lo **Step 2** è considerato completato; si può passare allo **Step 3** (es. API prenotazione, frontend, integrazioni).

---

## Test automatici (Step 1 + Step 2)

È disponibile una suite pytest che replica queste verifiche. Vedi `backend/tests/README.md`. Comandi dalla root:

- `make test` — esegue test backend e frontend
- `make test-backend` — solo test Step 1 + Step 2 (richiede PocketBase avviato)
- `make test-coverage` — test con report di coverage

Per i test Step 2 (hook) imposta `PB_ADMIN_EMAIL` e `PB_ADMIN_PASSWORD` con le credenziali del superuser PocketBase.
