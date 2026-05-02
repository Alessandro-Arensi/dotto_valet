# Dottò — Deploy demo (Vercel + Railway)

Guida step-by-step per pubblicare la demo. ~30 minuti.

**Architettura**:
- **Frontend** → Vercel (auto-deploy da GitHub)
- **Backend** → Railway (auto-deploy da GitHub, Dockerfile in `backend/`)
- **Database** → PostgreSQL su Railway (stesso progetto del backend: niente vendor esterno per DB)

---

## 1. Push su GitHub

```bash
cd /path/to/dotto_valet
git add -A
git commit -m "mvp demo ready"
git remote add origin git@github.com:<user>/dotto-valet.git  # se non già configurato
git push -u origin main
```

---

## 2. Database PostgreSQL su Railway

1. Vai su https://railway.app → **New Project** (o apri il progetto dove metterai il backend).
2. **New** → **Database** → **Add PostgreSQL**. Railway crea un service Postgres con variabili tipo `DATABASE_URL`, `PGHOST`, ecc.
3. Apri il service **Postgres** → scheda **Data** (o **Query** a seconda della UI) → esegui lo script SQL:
   - Incolla il contenuto di [db/schema.sql](db/schema.sql) ed esegui.
   - In alternativa, da locale: `psql "$DATABASE_URL" -f db/schema.sql` usando la connection string pubblica dalle **Variables** del Postgres (tab **Connect** / **Raw** `psql`).
4. Verifica le tabelle: `events`, `racks`, `operators`, `customers`, `tokens`, `checkins`, `slot_blocks`, `activity_logs`.
5. **Cambia la PIN dell’admin**. Stesso editor SQL:
   ```sql
   -- Genera un hash nuovo con bcrypt. Da locale:
   -- docker compose exec -T backend python -c "from app.services.auth import hash_pin; print(hash_pin('TUAPIN'))"
   UPDATE operators
   SET pin_hash = '$2b$12$...NUOVO_HASH...', phone = '+39TUONUMERO'
   WHERE is_admin = true;
   ```
6. **Collega il DB al backend**: sul service **backend** (lo crei allo step 3), **Variables** → **Add variable** → **Reference** → scegli il Postgres → `DATABASE_URL`. Così non copi password a mano e si aggiorna se Railway rigenera credenziali.

Formato tipico (interno o pubblico, a seconda di cosa espone Railway):

```
postgresql://postgres:PASSWORD@HOST:5432/railway
```

> Il backend converte automaticamente `postgresql://` → `postgresql+asyncpg://`. Niente da modificare sulla URL.

Con **un solo** processo uvicorn le connessioni dirette al Postgres vanno bene; non serve un pooler esterno come su altri host.

---

## 3. Backend su Railway

1. Nello stesso progetto: **New** → **GitHub Repo** → seleziona il repo (se non l’hai già collegato).
2. Al primo deploy Railway può auto-detect Node. **Settings** del service backend:
   - **Root Directory**: `backend`
   - **Builder**: Dockerfile (auto rileva `backend/Dockerfile`)
   - **Start Command**: vuoto (Dockerfile CMD lo gestisce)
3. **Variables** (obbligatorie), oltre al **reference** a `DATABASE_URL` del Postgres:
   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | *Reference* → Postgres → `DATABASE_URL` |
   | `JWT_SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
   | `APP_URL` | URL finale Vercel (placeholder ok all’inizio: `https://dotto-demo.vercel.app`) |
   | `CORS_ORIGINS` | URL Vercel (placeholder, aggiorni dopo) |
   | `ENVIRONMENT` | `production` |
   | `DEBUG` | `false` |

   Variabili Twilio facoltative (SMS disabilitato se omesse):
   | Key | Value |
   |-----|-------|
   | `TWILIO_ACCOUNT_SID` | (da Twilio) |
   | `TWILIO_AUTH_TOKEN` | (da Twilio) |
   | `TWILIO_PHONE_NUMBER` | numero mittente IT |

4. **Networking** → **Generate Domain**. Copia URL tipo `https://dotto-valet-production.up.railway.app`.
5. Verifica health: `curl https://<railway-url>/health` → `{"status":"healthy"}`.

---

## 4. Frontend su Vercel

1. Apri [frontend/vercel.json](frontend/vercel.json), sostituisci `REPLACE_WITH_RAILWAY_URL` con il dominio Railway (senza `https://`):
   ```json
   "destination": "https://dotto-valet-production.up.railway.app/api/:path*"
   ```
   Commit + push.
2. Vai su https://vercel.com → **Add New** → **Project** → importa il repo.
3. Configurazione:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Vite (auto-rilevato)
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: `dist` (default)
4. **Environment Variables**: nessuna richiesta (il proxy API passa via `vercel.json`).
5. Deploy. Copia URL tipo `https://dotto-demo.vercel.app`.

---

## 5. Chiudi il cerchio (aggiorna Railway)

Su Railway → **Variables** del backend:
- `APP_URL` → URL Vercel prod (es. `https://dotto-demo.vercel.app`)
- `CORS_ORIGINS` → URL Vercel prod. Se Vercel genera preview URLs separati, puoi usare wildcard `CORS_ORIGINS=https://dotto-demo.vercel.app,https://*.vercel.app`

Railway ri-deploya automaticamente al cambio env.

---

## 6. Test end-to-end

1. Apri `https://dotto-demo.vercel.app/login`
2. Login con telefono + PIN admin (impostati al punto 2.5)
3. **Eventi** → **Nuovo evento** → crea (rastrelliere auto-create)
4. Nuova tab: `https://dotto-demo.vercel.app/evento/<slug>` → **Prenota online** o `.../evento/<slug>/walkin`
5. Screenshot del QR
6. Torna operatore → **Check-out** → incolla codice `DOT-XXXX` → conferma

---

## Sottodominio Scintilla (post-demo)

Quando arrivano credenziali DNS:
1. Vercel → Project → **Settings** → **Domains** → add `valet.scintillacicloprogetti.it` (o sub scelto)
2. Aggiungi record CNAME come istruzioni Vercel
3. Aggiorna Railway:
   - `APP_URL=https://valet.scintillacicloprogetti.it`
   - `CORS_ORIGINS=https://valet.scintillacicloprogetti.it` (+ eventuali)

---

## Troubleshooting

**CORS errors sul browser**
- Verifica `CORS_ORIGINS` Railway contiene esattamente il dominio Vercel (HTTPS, no slash finale).

**401 Unauthorized su login**
- PIN admin sbagliato. Genera nuovo hash e `UPDATE operators` via query sul Postgres Railway (stesso punto dello schema).

**500 al caricamento evento**
- Schema DB non applicato o incompleto. Ri-esegui `db/schema.sql` sul Postgres Railway.

**`type "token_status" does not exist`**
- Backend vecchio. Trigger redeploy Railway (push dummy o **Redeploy** button).

**Vercel rewrite non funziona**
- Controlla `vercel.json` → `destination` senza `/api/:path*` finale porta a 404. La sintassi corretta è in questo repo.

**Backend non raggiunge il DB**
- Controlla che `DATABASE_URL` sul service backend sia un **reference** al Postgres nello stesso progetto (o una URL valida copiata dalle Variables del Postgres). Dopo rotazione password, il reference si aggiorna da solo.

---

## Costi demo

- **Railway**: Postgres + backend consumano lo stesso piano/crediti (es. $5/mese di credito trial poi uso a consumo); ordine di grandezza ~pochi $/mese per demo leggera.
- **Vercel**: hobby plan free (include bandwidth adeguato)
- **Twilio** (opzionale): trial credit iniziale + ~€0.08/SMS IT

*(Se un domani volessi anche il frontend su Railway, puoi aggiungere un service static o Nginx che serva `dist`; oggi Vercel resta la strada più semplice per lo SPA.)*
