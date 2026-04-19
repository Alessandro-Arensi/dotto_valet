# Dottò — Codebase Knowledge Dump

> **Audience**: another LLM (or engineer) tasked with implementing features, fixing bugs, or refactoring this repo without prior context.
> **Source of truth**: this document links every claim to a concrete file path. When in doubt, open the file.
> **Language note**: user-facing strings and domain terms are in Italian; code identifiers, this document, and comments below are in English.

---

## Table of Contents

1. [High-Level Overview](#1-high-level-overview)
2. [Tech Stack & Infrastructure](#2-tech-stack--infrastructure)
3. [Repository Layout](#3-repository-layout)
4. [System Architecture](#4-system-architecture)
5. [Data Model](#5-data-model)
6. [Feature-by-Feature Analysis](#6-feature-by-feature-analysis)
7. [Cross-Cutting Concerns](#7-cross-cutting-concerns)
8. [Nuances, Subtleties & Gotchas](#8-nuances-subtleties--gotchas)
9. [API Reference](#9-api-reference)
10. [Glossary](#10-glossary)
11. [Module / Symbol Reference](#11-module--symbol-reference)
12. [Assumptions & Open Questions](#12-assumptions--open-questions)

---

## 1. High-Level Overview

**Dottò** (pronounced "dot-TOH") is a bike valet management system for temporary events (concerts, festivals, markets). Built by [Scintilla Cicloprogetti](https://www.scintillacicloprogetti.it/). The project brief lives in [README.md](../README.md).

### 1.1 Business Purpose

Events that offer bike parking face three operational frictions:

1. Long queues at check-in (operator must identify, photograph, and assign a slot per bike).
2. Lost identification tokens (gettoni) with no way to reunite customer ↔ bike.
3. No pre-event signal of demand (operators cannot plan capacity).

Dottò addresses each:

| Friction            | Solution                                                                 |
|---------------------|--------------------------------------------------------------------------|
| Check-in queue      | Pre-event QR reservation; auto-slot assignment; skip-photo for digital   |
| Lost token          | Digital: recover via phone number. Physical: search by time + photo     |
| Unknown demand      | Public availability bar; operators see real-time occupancy + fast-mode hint |

### 1.2 Primary User Roles

- **Customer (public, unauthenticated)**: reserves a slot, receives QR via SMS, shows QR at check-in. Only contact: phone number (email optional). Uses:
  - [frontend/src/pages/public/EventPage.tsx](../frontend/src/pages/public/EventPage.tsx) — landing + reserve
  - [frontend/src/pages/public/TokenPage.tsx](../frontend/src/pages/public/TokenPage.tsx) — view QR + bike status
- **Operator / Admin (authenticated, phone + 4–6-digit PIN)**: runs check-in, check-out, dashboard. PIN login via [frontend/src/pages/operator/LoginPage.tsx](../frontend/src/pages/operator/LoginPage.tsx). Backed by bcrypt hashes in `operators.pin_hash`.

### 1.3 Core Feature Surface (and how features interact)

```
                ┌─────────────────────────────┐
                │   Event (parent container)  │
                │   - capacity, racks, dates  │
                └──┬──────────┬───────────────┘
                   │          │
           reserve │          │ has slots
                   ▼          ▼
        ┌────────────────┐  ┌──────┐
        │ Token          │  │ Rack │
        │ (digital|phys) │  │ +slot│
        └───┬───────┬────┘  └──┬───┘
        scan│       │reserve    │
            ▼       ▼           │
        ┌─────────────────────────────┐
        │  Checkin (token ↔ slot)     │ ◀── Operator
        └──────────┬──────────────────┘
                   │ checkout
                   ▼
        Digital → status=checked_out
        Physical → status=available (reusable)
```

Key interactions:

- **Reservation ↔ Check-in**: a reserved token is promoted to `checked_in` when scanned at the rack. No reservation? Operator can create-on-the-fly (digital or physical).
- **Check-in ↔ Check-out**: the `checkins` row is the pivot. `checked_out_at IS NULL` = active; set to `now()` = completed.
- **Event stats ↔ Operator UX**: Dashboard polls [events/{id}/stats](../backend/app/api/events.py#L60) every 30s; when `occupancy_percent ≥ fast_mode_threshold` (default 80%), UI shows "⚡ Modalità veloce consigliata".
- **Physical token ↔ Photo**: the photo is the only identifier if the gettone (physical token) is lost. Digital tokens skip the photo because the customer can always recover via phone.

---

## 2. Tech Stack & Infrastructure

Manifests: [backend/requirements.txt](../backend/requirements.txt), [frontend/package.json](../frontend/package.json), [docker-compose.yml](../docker-compose.yml), [env.example](../env.example).

### Backend

| Component       | Version  | Role                                          |
|-----------------|----------|-----------------------------------------------|
| Python          | 3.11-slim | Runtime                                       |
| FastAPI         | 0.109.0  | HTTP framework                                |
| uvicorn[standard]| 0.27.0  | ASGI server (`--reload` in dev)               |
| SQLAlchemy 2.0  | 2.0.25   | ORM, async mode                               |
| asyncpg         | 0.29.0   | Async PG driver                               |
| Alembic         | 1.13.1   | (declared; **no migrations directory present**) |
| Pydantic        | 2.5.3    | Request/response validation                   |
| pydantic-settings | 2.1.0  | `.env` loader                                 |
| phonenumbers    | 8.13.27  | E.164 normalization                           |
| python-jose[cryptography] | 3.3.0 | JWT                                       |
| passlib[bcrypt] | 1.7.4    | PIN hashing                                   |
| supabase        | 2.3.4    | Storage client                                |
| twilio          | 8.10.3   | SMS client (stub-safe when unconfigured)      |
| Pillow          | 10.2.0   | Image resize before upload                    |
| qrcode[pil]     | 7.4.2    | **Declared but not used** in backend code     |

### Frontend

| Component       | Version | Role                                          |
|-----------------|---------|-----------------------------------------------|
| React           | 18.2    | UI                                            |
| Vite            | 5.0     | Dev server + build                            |
| vite-plugin-pwa | 0.17    | PWA manifest + SW                             |
| Mantine (core/hooks/notifications/form) | 7.5 | UI library (**NOT Tailwind**)  |
| @tabler/icons-react | 2.46 | Icons                                       |
| TanStack Query  | 5.17    | Server state                                  |
| Zustand         | 4.4.7   | Auth state, persisted to localStorage         |
| React Router    | 6.21    | Routing                                       |
| html5-qrcode    | 2.3.8   | Camera QR scanner                             |
| qrcode.react    | 3.1.0   | Render QR on TokenPage                        |

### Infrastructure

- **Local dev**: [docker-compose.yml](../docker-compose.yml) brings up `db` (postgres:15 with schema seed), `backend` (FastAPI with code mount + reload), `frontend` (node:20 running `vite`). Frontend dev server proxies `/api` to `http://localhost:8000` (see [frontend/vite.config.ts:43-46](../frontend/vite.config.ts#L43)).
- **Cloud target**: Supabase for DB + object storage. Backend uses both `postgresql://…supabase.co` (via SQLAlchemy) and `supabase-py` (for the `bike-photos` bucket). See [supabase/SETUP.md](../supabase/SETUP.md).
- **Recommended hosting** (README, not wired): Vercel/Cloudflare Pages for FE, Railway/Render/Fly.io for BE.

### Environment Variables

Loaded via `pydantic-settings` in [backend/app/config.py](../backend/app/config.py):

```
DATABASE_URL, SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY
JWT_SECRET_KEY, JWT_ALGORITHM (default HS256), JWT_EXPIRE_MINUTES (default 480)
TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER
APP_URL (default https://dotto.bike), ENVIRONMENT, DEBUG
CORS_ORIGINS (comma-separated)
```

---

## 3. Repository Layout

```
dotto_valet/
├── README.md                # Italian project spec + UI mockups
├── LICENSE                  # MIT (assumed — check file)
├── docker-compose.yml       # 3-service local stack
├── env.example              # .env template
├── backend/
│   ├── Dockerfile           # python:3.11-slim + uvicorn
│   ├── requirements.txt
│   └── app/
│       ├── main.py          # FastAPI entry, CORS, router mounts
│       ├── config.py        # Settings / env
│       ├── database.py      # async engine, Base, get_db
│       ├── api/             # Routers (one file per feature area)
│       │   ├── auth.py      # /api/auth/*
│       │   ├── events.py    # /api/events/* (incl. public /availability, /reserve)
│       │   ├── checkin.py   # /api/checkin, /api/checkout, /api/checkins/{event_id}
│       │   └── tokens.py    # /api/token/* (incl. public QR lookup, /recover, /wallet)
│       ├── models/          # SQLAlchemy 2.0 Mapped[] style
│       │   ├── event.py, rack.py, operator.py, customer.py,
│       │   ├── token.py, checkin.py, activity_log.py
│       │   └── __init__.py  # re-exports all
│       ├── schemas/         # Pydantic request/response models
│       │   ├── event.py, token.py, checkin.py, operator.py, customer.py
│       │   └── __init__.py
│       └── services/        # Cross-router logic
│           ├── auth.py      # JWT + bcrypt + get_current_operator dependency
│           ├── token_service.py  # DOT-XXXX, E.164, get_or_create_customer, mask_phone
│           ├── sms.py       # Twilio (NOT CALLED from endpoints yet)
│           ├── storage.py   # Supabase upload_bike_photo (NOT CALLED from endpoints yet)
│           └── wallet.py    # Google Wallet stub (returns None)
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts       # React plugin + PWA + /api proxy
│   ├── tsconfig.json        # strict + noUnusedLocals
│   └── src/
│       ├── main.tsx         # Providers (QueryClient, Mantine, Router)
│       ├── App.tsx          # Route table + ProtectedRoute
│       ├── theme.ts         # Custom "dottoBlue" palette
│       ├── api/client.ts    # fetch wrapper + typed API clients + types
│       ├── stores/authStore.ts   # Zustand persisted auth
│       ├── components/
│       │   ├── common/QRScanner.tsx
│       │   └── layout/OperatorLayout.tsx
│       └── pages/
│           ├── operator/{LoginPage,DashboardPage,CheckinPage,CheckoutPage}.tsx
│           └── public/{EventPage,TokenPage}.tsx
└── supabase/
    ├── schema.sql           # Authoritative SQL: tables, CHECKs, views, functions, seed
    └── SETUP.md             # Supabase project bootstrap guide
```

**Missing relative to README spec** (not a bug — plan gaps):

- `backend/alembic/` — no migrations tree; schema is managed by `supabase/schema.sql` directly.
- `frontend/src/components/reservation/`, `checkin/`, `checkout/`, `search/` — not implemented; logic inlined in page components.
- `frontend/src/hooks/`, `frontend/src/pages/public/WalletPass.tsx`, `operator/SearchPage.tsx` — not implemented.
- `frontend/src/api/{events,tokens,checkin}.ts` — consolidated in `client.ts`.

---

## 4. System Architecture

### 4.1 Component Diagram & Request Flows

See [assets/architecture.md](assets/architecture.md) for Mermaid diagrams covering:

- Component map (client → frontend → backend → data + external services)
- Deployment topology (docker-compose)
- Check-in, reservation, and check-out sequence diagrams

### 4.2 Architecture Style

- **Layered monolith** on the backend: `api/` (routers) → `services/` (business logic) → `models/` (ORM) → `database.py` (session).
- **Dependency injection** via FastAPI `Depends`: `get_db` yields an `AsyncSession`; `get_current_operator` validates JWT and loads the operator. Admin-only routes use `get_current_admin` (declared but not yet used).
- **SPA + reverse proxy** on the frontend: Vite dev server proxies `/api/*` to uvicorn, so the client treats the API as same-origin and `api/client.ts` hardcodes `API_BASE = '/api'`.
- **Single-session transaction boundary**: every request gets one `AsyncSession` via `get_db()` which commits on exit or rolls back on exception — see [database.py:40-51](../backend/app/database.py#L40).

### 4.3 Frontend Structure

- Routes in [App.tsx](../frontend/src/App.tsx): public (`/evento/:slug`, `/t/:code`), auth (`/login`), protected operator shell (`/`, `/checkin`, `/checkout`) wrapped by `<ProtectedRoute>` → `<OperatorLayout>` with AppShell (header + navbar).
- **Auth persistence**: `useAuthStore` uses `zustand/middleware/persist` with key `'dotto-auth'` in localStorage — see [authStore.ts:19-46](../frontend/src/stores/authStore.ts#L19).
- **API client**: `fetchApi<T>()` in [client.ts:20-56](../frontend/src/api/client.ts#L20) reads the token from the store, adds `Authorization: Bearer`, and on 401 calls `logout()` — meaning token expiry silently logs the user out on the next authenticated call.
- **Data fetching**: every page uses `useQuery` / `useMutation`. `refetchInterval: 30000` is set on Dashboard stats + checkins. `queryClient.invalidateQueries` is called after check-in/check-out mutations to cascade-refresh Dashboard.

### 4.4 Backend Request Lifecycle

```
HTTP → CORSMiddleware (origins from env) → Router (prefix matches)
     → Dependency: get_db() opens AsyncSession
     → Dependency: get_current_operator() (for protected routes) decodes JWT, loads Operator
     → Endpoint body: SQL via select() / update(); object mutation
     → get_db's finally: session.commit() or rollback() on exception, then close()
     → Pydantic response_model serialization
```

No background workers, no message queue, no cache layer. All state is synchronous-per-request.

---

## 5. Data Model

Authoritative SQL: [supabase/schema.sql](../supabase/schema.sql). ORM mirror: [backend/app/models/](../backend/app/models/).

See [assets/er-diagram.md](assets/er-diagram.md) for the Mermaid ER diagram, constraint table, and token state machine.

### 5.1 Domain Model Cheatsheet

- `events`: parent aggregate. Slug-addressable public URL. Capacity governs `available`.
- `racks`: physical bike racks at an event. `(event_id, rack_number)` unique. Default 12 slots.
- `operators`: staff. PIN-authenticated. `is_admin` flag exists but admin-only guards are **not applied** to event-mutating endpoints (see §8).
- `customers`: minimal PII. `phone_normalized` (E.164) is the business key.
- `tokens`: QR identity. `code` like `DOT-XXXX` from alphabet `ABCDEFGHJKMNPQRSTUVWXYZ23456789` (omits `0`, `O`, `1`, `I`, `L`). Type and status CHECK-constrained.
- `checkins`: the bike-at-a-slot record. `token_id` is UNIQUE — so **a single token can only ever have one checkin row**. Physical tokens reuse the code only after their checkin is checked_out (and a **new** token row would be needed for a re-check-in, but currently the code transitions the existing token back to `available`; a subsequent check-in would collide on the UNIQUE constraint). See §8.2.
- `activity_logs`: audit trail. **No backend code inserts rows here yet** — the table is defined but dormant.

### 5.2 Computed Views & Functions

- `event_availability` VIEW and `available_slots` VIEW (see ER doc). Backend does **not** use these — it re-implements the logic in Python (`get_event_availability` and the rack-scan loops in `create_checkin` / `get_next_available_slot`).
- `generate_token_code()` SQL function: unused; Python equivalent in [token_service.py:21-36](../backend/app/services/token_service.py#L21).

### 5.3 Enum Storage

[backend/app/models/token.py:27-35](../backend/app/models/token.py#L27) declares SQLAlchemy `Enum(..., create_type=False)`. Combined with `schema.sql` which uses plain `VARCHAR + CHECK` (no PG enum type), the column is a VARCHAR at the DB level; `create_type=False` prevents Alembic/SQLAlchemy from attempting to CREATE TYPE.

---

## 6. Feature-by-Feature Analysis

Each feature below: **business purpose → entry points → controllers/services → DB touch → side effects → edge cases.**

### 6.1 Public Event Availability

- **Purpose**: tell a customer (and search engines) how many slots are left before they open a form. Zero friction before commitment.
- **Entry point**: `GET /api/events/{slug}/availability` ([events.py:152-203](../backend/app/api/events.py#L152)). No auth.
- **Frontend**: [EventPage.tsx:40-44](../frontend/src/pages/public/EventPage.tsx#L40) `useQuery(['eventAvailability', slug])`.
- **Logic**: SELECT event by slug + `is_active=true`; count tokens where `status IN (reserved, checked_in)`; compute `available`, `percent`, `can_reserve = available > 0 AND (end_date IS NULL OR end_date > now)`; attach a human message ("Sold out" / "Check-in apre il…").
- **Edge cases**:
  - Inactive or missing event → 404.
  - `total_capacity == 0` → division guarded (percent = 0).
  - `checkin_opens_at` in the future → user can still reserve but message advises the opening time.

### 6.2 Public Reservation

- **Purpose**: secure a slot before arrival; collect phone for SMS QR delivery.
- **Entry**: `POST /api/events/{slug}/reserve` ([events.py:220-307](../backend/app/api/events.py#L220)). No auth.
- **Frontend**: [EventPage.tsx:57-65](../frontend/src/pages/public/EventPage.tsx#L57) — **stub**. The form's `handleSubmit` currently shows a "Funzionalità in sviluppo" notification and does **not** POST. Wire-up required (see §8.1).
- **Logic**:
  1. Resolve active event by slug.
  2. Check capacity (token count with status in `reserved` / `checked_in`). Reject 400 if sold out.
  3. `get_or_create_customer(phone, email)` — normalizes phone via `phonenumbers.parse(default_region='IT')`; if `phonenumbers.is_valid_number`, formats E.164, otherwise strips non-digits (fallback). Existing customers get email filled if missing.
  4. Reject 400 if the same customer already has a reserved/checked_in token for this event (one-active-token rule).
  5. Generate unique `DOT-XXXX` (up to 10 retries on collision — raises if exhausted).
  6. INSERT `Token(type='digital', status='reserved', expires_at=event.end_date)`.
  7. Respond with `{code, qr_url, wallet_url}`.
- **Side effects intended but NOT wired**: Twilio SMS. `message_sent` is hardcoded `False` with a `# TODO: Send SMS via Twilio` comment at [events.py:292](../backend/app/api/events.py#L292). [services/sms.py](../backend/app/services/sms.py) has `send_reservation_sms` ready.
- **Edge case**: rate limiting is **not** implemented despite README calling for it.

### 6.3 Operator Login

- **Purpose**: authenticate event staff without passwords/accounts — PIN is enough on a shared device.
- **Entry**: `POST /api/auth/login` ([auth.py:17-63](../backend/app/api/auth.py#L17)). `GET /api/auth/me` returns current operator.
- **Frontend**: [LoginPage.tsx](../frontend/src/pages/operator/LoginPage.tsx). On success, persists JWT+operator via `useAuthStore.login()`.
- **Logic**: normalize phone to E.164 → lookup `operators` where `phone == normalized AND is_active`. **Fallback**: if no match, retry with the raw phone string (so seed data with `+39000000000` still works even if the input is `0000000000`). Verify PIN with `bcrypt.verify`. Issue JWT (`sub=operator_id`, `exp=now+480min`, `type=access`).
- **Edge cases**:
  - Deactivated operator → 401 even if PIN matches.
  - Token expiry handled client-side: any 401 triggers `logout()` in [client.ts:48-50](../frontend/src/api/client.ts#L48).

### 6.4 Event Dashboard

- **Purpose**: give operators a live picture: bikes in, free slots, occupancy %, recent traffic, suggest fast-mode when busy.
- **Entry**: protected route `/`. Uses `GET /api/events` (defaults `active_only=true`), `GET /api/events/{id}/stats`, `GET /api/checkins/{event_id}`.
- **Frontend**: [DashboardPage.tsx](../frontend/src/pages/operator/DashboardPage.tsx). Picks `events[0]` as the "active event" (no multi-event switcher yet). Polls stats + checkins every 30s.
- **Backend logic**: stats count tokens by status, count checkins in the last 5 minutes (used as a rate indicator but **not displayed** in UI yet), compute `suggest_fast_mode` from `fast_mode_threshold`.

### 6.5 Check-in

- **Purpose**: assign a physical slot to a bike in ≤30 seconds.
- **Entry**: `POST /api/checkin` ([checkin.py:31-232](../backend/app/api/checkin.py#L31)).
- **Frontend**: [CheckinPage.tsx](../frontend/src/pages/operator/CheckinPage.tsx). Three UI steps (`scan` / `form` / `physical`). QR scan via [QRScanner.tsx](../frontend/src/components/common/QRScanner.tsx) uses back-facing camera.
- **Three modes** (mutually exclusive):
  1. **Existing token** (reservation or physical): FE sends `{token_code}`. BE looks up token, validates status transitions from `reserved`/`available` → `checked_in`.
  2. **New digital on-the-spot**: FE sends `{create_token: true, customer_phone, ...}`. BE creates customer, checks 1-active-token rule, generates DOT code, inserts `Token(status='checked_in', reserved_at=now)`, picks the first active event.
  3. **Physical token**: FE flags `physical_token=true` and must supply `bike_photo_base64`. BE sets `token.type='physical'` and requires the photo (400 if absent).
- **Position assignment**:
  - `auto_position=true` (default): BE scans racks ordered by `rack_number`, for each fetches occupied slots (checkins where `checked_out_at IS NULL`), picks first free 1..`rack.slots`.
  - `auto_position=false`: FE supplies `{rack_id, slot_number}`; BE validates rack + slot availability. **However**, [CheckinPage.tsx:111-112](../frontend/src/pages/operator/CheckinPage.tsx#L111) passes `undefined` for both — manual selection UI is not implemented.
- **Photo upload**: currently placeholder. [checkin.py:188-193](../backend/app/api/checkin.py#L188) sets `bike_photo_url = "https://placeholder.com/photos/{code}.jpg"` and appends a warning. The real uploader [services/storage.py:upload_bike_photo](../backend/app/services/storage.py#L16) is wired to Supabase Storage bucket `bike-photos` with Pillow resize to 1200px + JPEG q85 — **but not called from the endpoint**.
- **Side effects intended, NOT wired**: SMS confirmation (`message_sent: False` hardcoded at [checkin.py:230](../backend/app/api/checkin.py#L230)); activity log row.
- **Edge cases**:
  - Customer already has active token → 400 "Customer already has an active token".
  - No active event in DB → 400 "No active event".
  - Token already checked in → 400.
  - All racks full → 400 "No available slots".

### 6.6 Check-out

- **Purpose**: return the bike, mark the slot free, close the token (digital) or recycle it (physical).
- **Entry**: `POST /api/checkout` ([checkin.py:235-298](../backend/app/api/checkin.py#L235)).
- **Frontend**: [CheckoutPage.tsx](../frontend/src/pages/operator/CheckoutPage.tsx). Scan QR → auto-fires the mutation → shows position + checked-in-at + photo (if any).
- **Logic**:
  1. SELECT token by code w/ eager-loaded `checkin.rack` and `customer`.
  2. Validate `status == 'checked_in'` and `checkin` exists.
  3. Set `checked_out_at`, `checked_out_by`.
  4. **Digital** token → `status = 'checked_out'` (terminal). **Physical** token → `status = 'available'` (reusable — gettone goes back in the tray).
- **Edge cases**:
  - Token already `checked_out` / `reserved` → 400 with status detail.
  - Missing checkin (data anomaly) → 400 "No checkin record found".
  - Physical token re-use currently **blocks** a subsequent check-in due to the `tokens.code` UNIQUE + `checkins.token_id` UNIQUE constraints — see §8.2.

### 6.7 List Active Check-ins

- `GET /api/checkins/{event_id}?status=active|all` — fuels the Dashboard table.
- [checkin.py:301-339](../backend/app/api/checkin.py#L301). Returns the last-in-first-out ordered list with masked customer phones (`mask_phone` shows first 4 + last 3 digits).

### 6.8 Token QR Page (public)

- **Purpose**: universal shareable link `https://dotto.bike/t/{code}` that shows QR + status + bike location.
- **Entry**: `GET /api/token/{code}` ([tokens.py:24-76](../backend/app/api/tokens.py#L24)). Frontend: [TokenPage.tsx](../frontend/src/pages/public/TokenPage.tsx) renders an in-page QR via `qrcode.react` pointing back at itself (`window.location.origin/t/{code}`).
- Position string is built backend-side: "Rastrelliera {n}, Slot {s}" or "{rack.label}, Slot {s}".

### 6.9 Token Recovery (lost digital QR)

- **Purpose**: client lost the QR but remembers their phone number — we re-surface the active token.
- **Entry**: `GET /api/token/recover?phone=…[&event_id=…]` ([tokens.py:79-128](../backend/app/api/tokens.py#L79)).
- **Logic**: normalize phone, join to customers by `phone_normalized`, filter `type='digital'` and status in `reserved|checked_in`. Returns list (usually 1).
- **⚠ Route order bug** — see §8.3.

### 6.10 Google Wallet Pass

- **Purpose**: let customer add QR to Google Wallet.
- **Entry**: `GET /api/token/{code}/wallet` ([tokens.py:131-175](../backend/app/api/tokens.py#L131)).
- **Status**: `services/wallet.py` is a **stub** — builds the pass JSON, prints it, returns `None`. The endpoint responds with `{success: false, setup: get_wallet_instructions()}` when unconfigured.

---

## 7. Cross-Cutting Concerns

### 7.1 Authentication & Authorization

- **Scheme**: Bearer JWT, `HS256`, 8-hour default expiry. Secret in `JWT_SECRET_KEY` (docker-compose hardcodes a dev secret — **must override in prod**: [docker-compose.yml:37](../docker-compose.yml#L37)).
- **Hashing**: bcrypt via passlib. PIN min 4 / max 6 digits (frontend-enforced in [operator.py:13](../backend/app/schemas/operator.py#L13)).
- **Dependencies**: every protected router uses `operator: Operator = Depends(get_current_operator)`. There is also a `get_current_admin` defined ([services/auth.py:93-102](../backend/app/services/auth.py#L93)) but **not attached** to any endpoint — including event list/creation, which any operator can currently read.

### 7.2 Phone Handling

- Normalized by `phonenumbers` with `default_region='IT'` in [token_service.py:39-48](../backend/app/services/token_service.py#L39). Falls back to a digits+plus cleanup if parse fails — meaning invalid numbers still persist in the DB as whatever was entered, which can break uniqueness checks on re-entry (same human inputting in a different format creates a second customer row).
- Masking for UI uses `phone[:4] + "****" + phone[-3:]` — see [token_service.py:51-56](../backend/app/services/token_service.py#L51).

### 7.3 CORS

Configured in [main.py:37-43](../backend/app/main.py#L37) from `CORS_ORIGINS` env. Permissive methods/headers; credentials allowed.

### 7.4 Error Surface

- Backend raises `HTTPException` with human-readable `detail` (mostly English). Frontend surfaces `error.detail` via `notifications.show({ color: 'red' })` or inline `<Alert>`. No error taxonomy / codes.

### 7.5 Logging / Observability

- **None structured**. `print()` calls in [sms.py](../backend/app/services/sms.py), [storage.py](../backend/app/services/storage.py), [wallet.py](../backend/app/services/wallet.py), and the lifespan handler. SQLAlchemy `echo=settings.debug` prints SQL in dev only.

### 7.6 Rate Limiting

- **Not implemented**. README calls for it on `/reserve` and `/send-ticket`.

### 7.7 Internationalization

- No i18n framework. All user strings are Italian, directly in JSX and SMS templates. Backend error `detail` strings are English. Translation would require extraction or a library.

### 7.8 PWA

- Configured in [vite.config.ts:9-38](../frontend/vite.config.ts#L9). Manifest + autoUpdate SW. Icon assets (`pwa-192x192.png`, `pwa-512x512.png`, `apple-touch-icon.png`, `mask-icon.svg`) are **referenced but not present** in the repo — add before building or remove from `includeAssets`.

---

## 8. Nuances, Subtleties & Gotchas

Things you **must** know before changing code.

### 8.1 Public reservation UI is a stub

[EventPage.tsx:58-65](../frontend/src/pages/public/EventPage.tsx#L58) does not call `/api/events/{slug}/reserve`. It shows "Funzionalità in sviluppo". The success branch (`reserved && tokenCode`) renders a confirmation but `tokenCode` is never set. Add a mutation using the existing backend endpoint.

### 8.2 Physical token re-checkin will fail

Sequence:
1. Physical token `DOT-ABCD` seeded with `status='available'`.
2. First check-in creates `checkin(token_id=...)`; sets `token.status='checked_in'`.
3. Checkout sets `token.status='available'` (physical branch at [checkin.py:273](../backend/app/api/checkin.py#L273)). The `checkins` row is kept with `checked_out_at` set.
4. Next customer uses the same gettone: `POST /api/checkin {token_code: 'DOT-ABCD'}` — passes status check.
5. INSERT new `checkins` row → violates `UNIQUE(token_id)`.

**Options**: allow multiple checkin rows per token_id (drop UNIQUE) and rely on `UNIQUE(rack_id, slot_number, checked_out_at)` for slot integrity; OR mint a new token row per physical reuse. Current schema.sql enforces one-shot.

### 8.3 `/api/token/recover` shadowed by `/{code}`

In [tokens.py](../backend/app/api/tokens.py), `router.get("/{code}")` (line 24) is registered **before** `router.get("/recover")` (line 79). FastAPI matches in declaration order, so `GET /api/token/recover` matches `get_token_info(code="recover")` and returns 404 "Token not found". Fix: move `recover` route above `{code}` OR rename the path to avoid collision (e.g. `/api/token/_recover`, or make it POST).

### 8.4 Google Wallet returns None

[services/wallet.py:106-108](../backend/app/services/wallet.py#L106) prints the pass JSON and always returns `None`. The endpoint does its best to explain this (`setup: get_wallet_instructions()`), but frontend buttons ("📲 Aggiungi a Google Wallet") go nowhere — wire a click handler or hide the button when unconfigured.

### 8.5 Photo upload not wired

Backend accepts `bike_photo_base64`, stores placeholder URL. The real uploader exists in `services/storage.py` and even resizes + re-encodes with Pillow — just unused by the endpoint. Also, large base64 strings sent as JSON bodies will hit FastAPI's default request limits; consider multipart or a direct-upload signed URL pattern.

### 8.6 SMS is a stub

[services/sms.py:16-18](../backend/app/services/sms.py#L16) prints a log if Twilio isn't configured and returns `False`. All three callers (`send_reservation_sms`, `send_checkin_sms`, `send_token_recovery_sms`) exist — but **no endpoint calls them**. `message_sent` in responses is hardcoded `False`.

### 8.7 Active event is implicit

Dashboard and check-in both use `events[0]` from a `list_events(active_only=True)` — no explicit "current event" switcher. If two events are active simultaneously, behavior depends on ORDER BY `start_date DESC` (see [events.py:36](../backend/app/api/events.py#L36)). For multi-venue operation, a selector (or `/api/events/active`) is needed.

### 8.8 ActivityLog table is dormant

The `activity_logs` table, `ActivityLog` model, and supporting index exist but **nothing writes to them**. Any audit requirement (who overrode a lost-token recovery, who moved a slot, etc.) must be added in the relevant endpoint + likely a helper in `services/`.

### 8.9 Auto-position race condition

`create_checkin` with `auto_position=true` scans racks in Python, picks a slot, then INSERTs without taking a DB lock. Under concurrent check-ins, two operators can be assigned the same slot; the INSERT will then fail the `UNIQUE(rack_id, slot_number, checked_out_at)` constraint — returning a 500. Mitigation: wrap the scan + insert in a `SELECT … FOR UPDATE` on the rack, or retry on `IntegrityError`, or precompute slots via the PG `get_next_available_slot` function inside a transaction.

### 8.10 Frontend manual rack selection is a dead path

[CheckinPage.tsx:111-112](../frontend/src/pages/operator/CheckinPage.tsx#L111) explicitly passes `undefined` for `rack_id` / `slot_number` with a `// TODO: manual selection` comment. Toggling auto-position off will cause the backend to 400. Until the selector exists, the Switch is misleading.

### 8.11 Phone normalization silent fallback

If `phonenumbers.parse` fails (e.g. input like `ciao`), [token_service.py:47-48](../backend/app/services/token_service.py#L47) returns whatever digits+`+` the user typed. That becomes `phone_normalized` and will break the `UNIQUE(phone_normalized)` constraint in subtle ways (two different invalid inputs from the same user → two customers). Consider rejecting invalid numbers at the API boundary.

### 8.12 Zustand persist and token expiry

`useAuthStore` persists `{token, operator, isAuthenticated}` to `localStorage` under key `dotto-auth`. When the JWT expires mid-session, the store still says `isAuthenticated=true` until the next 401 triggers `logout()`. A reader loading the app fresh can hit a "stale authenticated" moment. A guard that validates the token client-side (decode exp) would close this hole.

### 8.13 docker-compose dev JWT secret

The compose file sets `JWT_SECRET_KEY: dev-secret-key-change-in-production` inline ([docker-compose.yml:37](../docker-compose.yml#L37)). Any production deploy **must** set this via env override; the default value in Settings is not used because compose always injects one.

### 8.14 `noUnusedLocals: true` + dead imports

Frontend `tsconfig.json` enforces `noUnusedLocals` / `noUnusedParameters` ([tsconfig.json:19-20](../frontend/tsconfig.json#L19)). Several pages import symbols they don't use (e.g. `Event, EventStats, CheckinItem` aliasing in DashboardPage). `npm run lint` (ESLint `--max-warnings 0`) may fail a CI build until cleaned up. Verify before committing.

### 8.15 Check-in with `create_token` ignores `token_code`

When `create_token=true`, the backend skips token lookup entirely. The frontend nonetheless sends `token_code: "NEW-${Date.now()}"` ([CheckinPage.tsx:104](../frontend/src/pages/operator/CheckinPage.tsx#L104)). Works today because nothing validates the placeholder, but a future Pydantic `Field(pattern=r"^DOT-\w{4}$")` on `token_code` would break it.

---

## 9. API Reference

Base path: `/api`. Auth via `Authorization: Bearer <JWT>` unless marked "Public". Full specs in code — this is a reference index.

### 9.1 Auth

| Method | Path                  | Auth | Body / Query | Response                         | Source                                                  |
|--------|-----------------------|------|--------------|----------------------------------|---------------------------------------------------------|
| POST   | `/api/auth/login`     | No   | `{phone, pin}` | `{access_token, token_type, operator}` | [auth.py:17](../backend/app/api/auth.py#L17) |
| GET    | `/api/auth/me`        | Yes  | —            | `{id, name, is_admin}`           | [auth.py:66](../backend/app/api/auth.py#L66)            |

### 9.2 Events

| Method | Path                                     | Auth | Purpose                              | Source |
|--------|------------------------------------------|------|--------------------------------------|--------|
| GET    | `/api/events?active_only=true`           | Yes  | List events                          | [events.py:29](../backend/app/api/events.py#L29) |
| GET    | `/api/events/{event_id}`                 | Yes  | Event detail                         | [events.py:44](../backend/app/api/events.py#L44) |
| GET    | `/api/events/{event_id}/stats`           | Yes  | Real-time stats incl. `suggest_fast_mode` | [events.py:60](../backend/app/api/events.py#L60) |
| GET    | `/api/events/{event_id}/next-slot`       | Yes  | First free `(rack, slot)`            | [events.py:112](../backend/app/api/events.py#L112) |
| GET    | `/api/events/{slug}/availability`        | **No**  | Public availability page data     | [events.py:153](../backend/app/api/events.py#L153) |
| POST   | `/api/events/{slug}/reserve`             | **No**  | Public reservation → new token    | [events.py:220](../backend/app/api/events.py#L220) |

**⚠ Path collision risk**: both `/api/events/{event_id}` (UUID) and `/api/events/{slug}/availability` live on `/events`. FastAPI path parameters don't enforce UUID, so a slug request to `GET /api/events/concerto` routes to `get_event(event_id='concerto')` and returns 422 on UUID parse. Availability avoids this by adding `/availability` suffix; just note that plain `/api/events/{slug}` is not valid.

### 9.3 Check-in / Check-out

| Method | Path                                | Auth | Purpose                         | Source |
|--------|-------------------------------------|------|----------------------------------|--------|
| POST   | `/api/checkin`                      | Yes  | Create checkin / or new token+checkin | [checkin.py:31](../backend/app/api/checkin.py#L31) |
| POST   | `/api/checkout`                     | Yes  | Close checkin                   | [checkin.py:235](../backend/app/api/checkin.py#L235) |
| GET    | `/api/checkins/{event_id}?status=active|all` | Yes | List checkins | [checkin.py:301](../backend/app/api/checkin.py#L301) |

### 9.4 Tokens

| Method | Path                         | Auth | Purpose                          | Source |
|--------|------------------------------|------|-----------------------------------|--------|
| GET    | `/api/token/{code}`          | **No**  | Public QR page data           | [tokens.py:24](../backend/app/api/tokens.py#L24) |
| GET    | `/api/token/recover?phone=`  | **No**  | Recover digital token by phone — ⚠ [blocked by route order](../backend/app/api/tokens.py#L79) | [tokens.py:79](../backend/app/api/tokens.py#L79) |
| GET    | `/api/token/{code}/wallet`   | **No**  | Google Wallet pass URL (stub) | [tokens.py:131](../backend/app/api/tokens.py#L131) |

### 9.5 System

| Method | Path      | Auth | Response                                | Source |
|--------|-----------|------|-----------------------------------------|--------|
| GET    | `/`       | No   | `{name, version, status, docs}`         | [main.py:52](../backend/app/main.py#L52) |
| GET    | `/health` | No   | `{status: healthy}`                     | [main.py:63](../backend/app/main.py#L63) |
| GET    | `/docs`   | No   | Swagger UI (**only when DEBUG=true**)   | [main.py:32](../backend/app/main.py#L32) |
| GET    | `/redoc`  | No   | ReDoc (**only when DEBUG=true**)        | [main.py:33](../backend/app/main.py#L33) |

### 9.6 Example Payloads

**POST `/api/checkin` (new digital)**
```json
{
  "token_code": "NEW-ignored",
  "create_token": true,
  "customer_phone": "+39 333 1234567",
  "customer_email": "mario@example.it",
  "newsletter_opt_in": true,
  "physical_token": false,
  "auto_position": true
}
```

**POST `/api/checkin` (existing reservation)**
```json
{ "token_code": "DOT-A7X9", "auto_position": true }
```

**POST `/api/checkin` (physical, manual slot)**
```json
{
  "token_code": "DOT-K8M2",
  "physical_token": true,
  "auto_position": false,
  "rack_id": "<uuid>",
  "slot_number": 7,
  "bike_photo_base64": "data:image/jpeg;base64,..."
}
```

---

## 10. Glossary

| Term (IT / code)             | English / meaning                                                        |
|------------------------------|--------------------------------------------------------------------------|
| **Dottò**                    | Product name. Italian informal for "doctor" — i.e. a bike caretaker.     |
| **Rastrelliera** / `rack`    | Physical bike rack, holding N numbered slots.                            |
| **Slot**                     | Single bike spot within a rack, 1..`rack.slots`.                         |
| **Gettone** / `physical token` | Plastic/metal QR-laminated disc reused across customers.               |
| **Token digitale**           | A `tokens` row with `type='digital'` tied 1:1 to a customer+event.       |
| **Token fisico**             | `type='physical'`. Reusable across events (schema permits; see §8.2).    |
| **Prenotazione** / reservation | A `tokens` row with `status='reserved'`, no checkin yet.              |
| **Check-in**                 | Operator scans token → creates `checkins` row with rack+slot → `status='checked_in'`. |
| **Check-out**                | Operator scans token → sets `checked_out_at` → digital becomes `checked_out`, physical → `available`. |
| **Modalità veloce** / fast mode | UI hint when occupancy ≥ `fast_mode_threshold` (default 80%). Not a backend toggle. |
| **Posizione automatica**     | `auto_position=true`: backend picks first free slot.                     |
| **PIN login**                | Operator auth scheme (phone + 4–6 digit PIN, bcrypt-hashed).             |
| **DOT-XXXX**                 | Token code format; alphabet excludes `0 O 1 I L` for legibility.         |
| **Newsletter opt-in**        | `customers.newsletter_opt_in` flag (no backend code consumes it yet).    |

---

## 11. Module / Symbol Reference

### Backend

| Module                                    | Key symbols                                                         |
|-------------------------------------------|----------------------------------------------------------------------|
| [backend/app/main.py](../backend/app/main.py) | `app: FastAPI`, `lifespan`, router mounts                        |
| [backend/app/config.py](../backend/app/config.py) | `Settings`, `get_settings()` (lru_cached)                    |
| [backend/app/database.py](../backend/app/database.py) | `engine`, `AsyncSessionLocal`, `Base`, `get_db()`         |
| [backend/app/models/event.py](../backend/app/models/event.py) | `Event` (relationships: racks, tokens, checkins)       |
| [backend/app/models/rack.py](../backend/app/models/rack.py) | `Rack` (`UniqueConstraint(event_id, rack_number)`)        |
| [backend/app/models/operator.py](../backend/app/models/operator.py) | `Operator` (`pin_hash`, `is_admin`)                |
| [backend/app/models/customer.py](../backend/app/models/customer.py) | `Customer` (unique `phone_normalized`)             |
| [backend/app/models/token.py](../backend/app/models/token.py) | `Token`, `TokenType`, `TokenStatus` literals           |
| [backend/app/models/checkin.py](../backend/app/models/checkin.py) | `Checkin` (unique `token_id`, `manual_override`)    |
| [backend/app/models/activity_log.py](../backend/app/models/activity_log.py) | `ActivityLog` (`metadata_` → column "metadata") |
| [backend/app/api/auth.py](../backend/app/api/auth.py) | `login`, `get_me`                                          |
| [backend/app/api/events.py](../backend/app/api/events.py) | `list_events`, `get_event`, `get_event_stats`, `get_next_available_slot`, `get_event_availability`, `create_reservation` |
| [backend/app/api/checkin.py](../backend/app/api/checkin.py) | `create_checkin`, `create_checkout`, `list_checkins`      |
| [backend/app/api/tokens.py](../backend/app/api/tokens.py) | `get_token_info`, `recover_token`, `get_wallet_pass`       |
| [backend/app/services/auth.py](../backend/app/services/auth.py) | `verify_pin`, `hash_pin`, `create_access_token`, `decode_token`, `get_current_operator`, `get_current_admin` |
| [backend/app/services/token_service.py](../backend/app/services/token_service.py) | `generate_token_code`, `get_unique_token_code`, `normalize_phone`, `mask_phone`, `get_or_create_customer` |
| [backend/app/services/sms.py](../backend/app/services/sms.py) | `send_sms`, `send_reservation_sms`, `send_checkin_sms`, `send_token_recovery_sms` |
| [backend/app/services/storage.py](../backend/app/services/storage.py) | `upload_bike_photo`, `delete_bike_photo`           |
| [backend/app/services/wallet.py](../backend/app/services/wallet.py) | `generate_wallet_pass_url`, `get_wallet_instructions` |

### Frontend

| Module                                                    | Key symbols                                                     |
|-----------------------------------------------------------|------------------------------------------------------------------|
| [frontend/src/main.tsx](../frontend/src/main.tsx)         | `QueryClientProvider`, `MantineProvider`, `BrowserRouter`        |
| [frontend/src/App.tsx](../frontend/src/App.tsx)           | `ProtectedRoute`, route table                                    |
| [frontend/src/theme.ts](../frontend/src/theme.ts)         | `theme` with `dottoBlue` palette                                 |
| [frontend/src/api/client.ts](../frontend/src/api/client.ts) | `ApiError`, `fetchApi`, `authApi`, `eventsApi`, `checkinApi`, `tokenApi`; shared TS types |
| [frontend/src/stores/authStore.ts](../frontend/src/stores/authStore.ts) | `useAuthStore` (Zustand persisted)                   |
| [frontend/src/components/common/QRScanner.tsx](../frontend/src/components/common/QRScanner.tsx) | `QRScanner({onScan, onClose})` — html5-qrcode |
| [frontend/src/components/layout/OperatorLayout.tsx](../frontend/src/components/layout/OperatorLayout.tsx) | AppShell wrapper                         |
| [frontend/src/pages/operator/LoginPage.tsx](../frontend/src/pages/operator/LoginPage.tsx) | PIN login                                         |
| [frontend/src/pages/operator/DashboardPage.tsx](../frontend/src/pages/operator/DashboardPage.tsx) | Stats + active checkins table                 |
| [frontend/src/pages/operator/CheckinPage.tsx](../frontend/src/pages/operator/CheckinPage.tsx) | 3-step scan/form/physical                         |
| [frontend/src/pages/operator/CheckoutPage.tsx](../frontend/src/pages/operator/CheckoutPage.tsx) | Scan → mutate → show result                     |
| [frontend/src/pages/public/EventPage.tsx](../frontend/src/pages/public/EventPage.tsx) | Availability + reservation form (stub submit)       |
| [frontend/src/pages/public/TokenPage.tsx](../frontend/src/pages/public/TokenPage.tsx) | QR + status + position                              |

---

## 12. Assumptions & Open Questions

| ID   | Assumption                                                                 | Confidence | Verification                                         |
|------|----------------------------------------------------------------------------|------------|------------------------------------------------------|
| A1   | Alembic is aspirational; schema is managed via `supabase/schema.sql` seed. | High       | No `alembic/` directory, `alembic.ini`, or migrations dir. |
| A2   | A single event is considered "active" at any time (`events[0]`).           | High       | Hardcoded in Dashboard + Check-in frontend.          |
| A3   | Physical tokens are seeded via DB inserts, not an admin UI.                | High       | No admin CRUD endpoints exist.                       |
| A4   | SMS, Google Wallet, photo upload are known TODOs, not missing spec.        | High       | Explicit `TODO` comments / placeholder returns.      |
| A5   | The production deployment will run behind HTTPS and override `JWT_SECRET_KEY`. | Medium | docker-compose bakes a dev secret; `env.example` marks it secret. |
| A6   | `phone` column storing pre-normalization format is intentional (for display). | Medium  | Model has both `phone` and `phone_normalized`; no comment explains why. |
| A7   | `ActivityLog` is intended for a later audit feature, not dead code.        | Medium     | Schema indexed for time-series; no writes yet.       |
| A8   | Frontend page-level state (no global business store beyond auth) is acceptable. | High | Zustand only hosts auth; everything else is `useQuery`. |

### Open Questions

1. Should physical tokens allow multiple lifetime checkins (drop `checkins.token_id UNIQUE`) or mint new token rows per reuse?
2. Is the `checkin_opens_at` gate enforced server-side? Currently availability endpoint returns an informational message but `reserve` does not reject pre-open reservations.
3. Who will own cross-event admin features (create event, seed racks, import physical tokens)? No endpoints exist; likely Supabase Studio + direct SQL for now.
4. Rate limit placement: in-app (slowapi middleware) or edge (Cloudflare / reverse proxy)?
5. Should reservation SMS be sent synchronously (blocking the HTTP response) or via a queue? No queue exists.

---

## Appendix: How to Re-derive This Document

If the repo grows beyond what this doc covers, re-run exploration in this order:

1. `Glob **/*` then `ls` of `backend/` and `frontend/` to detect new directories.
2. Read [README.md](../README.md) + [docker-compose.yml](../docker-compose.yml) + [env.example](../env.example) for intent + topology.
3. Read [supabase/schema.sql](../supabase/schema.sql) before any ORM file — the SQL is authoritative.
4. Walk backend: `main.py → config.py → database.py → api/*.py → services/*.py → models/*.py → schemas/*.py`.
5. Walk frontend: `main.tsx → App.tsx → api/client.ts → stores/authStore.ts → pages/*.tsx`.
6. Grep for `TODO`, `FIXME`, `placeholder`, `stub` — each one is a known gap worth noting in §8.
7. Check `git log --oneline -20` for recent architectural shifts not reflected here.

End of document.
