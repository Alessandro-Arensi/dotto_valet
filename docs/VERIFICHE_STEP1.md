# Verifiche Step 1 – Setup PocketBase

Esegui queste verifiche dopo aver completato lo **Step 1** (PocketBase: directory, Docker, collections, storage, API rules) per confermare che tutto funzioni.

---

## 1. Build e avvio

```bash
make build
make up-pocketbase
# oppure: make up   (avvia tutti i servizi)
```

- **Verifica:** nessun errore in build; container `pocketbase` in esecuzione.
- **Comando:** `docker-compose ps` → `pocketbase` deve essere `Up`.

---

## 2. Log e migration

```bash
make logs-pocketbase
# oppure: docker-compose logs pocketbase
```

- **Verifica:** nel log non compare `Error: Failed to apply migration`.
- **Verifica:** compare una riga tipo `Server started at http://0.0.0.0:8090` e (al primo avvio) il link per creare il superuser.

---

## 3. API health

```bash
curl -s http://localhost:8090/api/health
```

- **Verifica:** risposta JSON con `"code":200` o `"message":"API is healthy."`.

---

## 4. Collections create

```bash
curl -s "http://localhost:8090/api/collections/events/records"
curl -s "http://localhost:8090/api/collections/tokens/records"
curl -s "http://localhost:8090/api/collections/racks/records"
curl -s "http://localhost:8090/api/collections/operators/records"
```

- **Verifica:** per ognuno risposta HTTP 200 e JSON con `"items":[]` (liste vuote). Se ricevi 404, la collection non esiste.

---

## 5. Primo superuser (obbligatorio al primo avvio)

- **Opzione A – Browser:** apri http://localhost:8090/_/ e completa la procedura guidata (email + password).
- **Opzione B – Terminale:**
  ```bash
  docker-compose exec pocketbase /usr/local/bin/pocketbase superuser upsert TUA_EMAIL TUA_PASSWORD
  ```

- **Verifica:** riesci ad accedere alla Admin UI (http://localhost:8090/_/) con le credenziali scelte.

---

## 6. Admin UI – schema collections

Nella Admin UI (http://localhost:8090/_/):

- **Verifica:** esistono le collection **events**, **racks**, **operators**, **tokens**.
- **Verifica:** in **events** ci sono i campi: name, slug, location, start_date, end_date, total_capacity, slots_available, checkin_opens_at, is_active.
- **Verifica:** in **tokens** ci sono: event, email, phone, token_code, token_type (digital/physical), status, rack, slot_num, photo (file), newsletter_opt_in, whatsapp_sent.

---

## 7. (Opzionale) Creare un evento di test

Dalla Admin UI:

1. Apri la collection **events**.
2. Crea un record: name, slug, location, date, total_capacity e slots_available uguali (es. 120), is_active = true.
3. **Verifica:** il record viene salvato e compare in lista.

Poi:

```bash
curl -s "http://localhost:8090/api/collections/events/records?filter=(is_active=true)"
```

- **Verifica:** nella risposta compare l’evento creato (anche senza auth, se la listRule lo consente).

---

## Riepilogo checklist Step 1

| # | Verifica | Comando / azione |
|---|----------|-------------------|
| 1 | Build e container avviato | `make build` + `make up-pocketbase` + `docker-compose ps` |
| 2 | Nessun errore migration nei log | `make logs-pocketbase` |
| 3 | API health 200 | `curl -s http://localhost:8090/api/health` |
| 4 | Le 4 collection rispondono | `curl` su events, tokens, racks, operators |
| 5 | Superuser creato e login Admin OK | Browser o `pocketbase superuser upsert` |
| 6 | Schema collections corretto in Admin UI | Controllo manuale in http://localhost:8090/_/ |
| 7 | (Opzionale) Evento di test creato e visibile via API | Creare evento in Admin + `curl` con filter |

Se tutte le verifiche passano, lo **Step 1** è considerato completato e si può passare allo **Step 2** (hook PocketBase).  
→ Vedi [VERIFICHE_STEP2.md](VERIFICHE_STEP2.md).
