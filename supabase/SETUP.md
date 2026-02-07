# Setup Supabase per Dottò

## 1. Creare Progetto Supabase

1. Vai su [supabase.com](https://supabase.com) e accedi
2. Clicca "New Project"
3. Configura:
   - **Name**: `dotto`
   - **Database Password**: genera una password sicura (salvala!)
   - **Region**: scegli la più vicina (es. Frankfurt per EU)
4. Attendi che il progetto sia pronto (~2 minuti)

## 2. Configurare il Database

1. Vai su **SQL Editor** nel menu laterale
2. Clicca "New query"
3. Copia e incolla il contenuto di `schema.sql`
4. Clicca "Run" per eseguire

## 3. Configurare Storage (per foto bici)

1. Vai su **Storage** nel menu laterale
2. Clicca "New bucket"
3. Configura:
   - **Name**: `bike-photos`
   - **Public bucket**: No (le foto sono private)
4. Clicca "Create bucket"

### Policies per Storage

Aggiungi queste policies per il bucket `bike-photos`:

```sql
-- Policy: operatori possono caricare foto
CREATE POLICY "Operators can upload photos"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'bike-photos');

-- Policy: operatori possono vedere foto
CREATE POLICY "Operators can view photos"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'bike-photos');
```

## 4. Ottenere le Credenziali

1. Vai su **Settings** > **API**
2. Copia:
   - **Project URL**: `https://xxxxx.supabase.co`
   - **Publishable key** (`sb_publishable_...`): per il frontend
   - **Secret key** (`sb_secret_...`): per il backend (SEGRETA!)

3. Vai su **Settings** > **Database**
4. Copia:
   - **Connection string**: per SQLAlchemy
   - Sostituisci `[YOUR-PASSWORD]` con la password del DB

## 5. Configurare Environment Variables

Crea il file `.env` nella root del progetto (copia da `.env.example`):

```bash
cp .env.example .env
```

Compila con le tue credenziali.

## 6. Testare la Connessione

```bash
cd backend
python -c "from app.database import engine; print('OK')"
```


