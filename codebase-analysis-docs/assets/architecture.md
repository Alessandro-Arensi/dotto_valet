# Architecture Diagram — Dottò

## Component Map

```mermaid
flowchart LR
    subgraph Client["Client Tier"]
        CU[Customer Browser<br/>Mobile PWA]
        OP[Operator Tablet/Phone<br/>PWA]
    end

    subgraph Frontend["Frontend — Vite + React 18"]
        direction TB
        Router[React Router v6<br/>App.tsx]
        PubPage[Public Pages<br/>EventPage / TokenPage]
        OpPage[Operator Pages<br/>Login / Dashboard / Checkin / Checkout]
        Store[Zustand authStore<br/>persist localStorage]
        QRY[TanStack Query<br/>queryClient]
        APIC[api/client.ts<br/>fetch wrapper]
        QR[QRScanner<br/>html5-qrcode]
    end

    subgraph Backend["Backend — FastAPI (Python 3.11)"]
        direction TB
        Main[main.py<br/>CORS + lifespan]
        RAuth[auth.py<br/>/api/auth/*]
        REvt[events.py<br/>/api/events/*]
        RCk[checkin.py<br/>/api/checkin /checkout /checkins]
        RTok[tokens.py<br/>/api/token/*]
        SAuth[services/auth.py<br/>JWT + bcrypt]
        STok[services/token_service.py<br/>E.164 / DOT-XXXX]
        SSMS[services/sms.py<br/>Twilio]
        SWlt[services/wallet.py<br/>Google Wallet stub]
        SStor[services/storage.py<br/>Supabase Storage]
    end

    subgraph Data["Data Tier"]
        PG[(PostgreSQL 15<br/>SQLAlchemy async/asyncpg)]
        SB[(Supabase Storage<br/>bucket: bike-photos)]
    end

    subgraph External["External"]
        TW[Twilio SMS]
        GW[Google Wallet API]
    end

    CU --> PubPage
    OP --> OpPage
    PubPage --> APIC
    OpPage --> APIC
    OpPage --> QR
    APIC --> QRY
    OpPage --> Store
    APIC -- "/api/*" --> Main
    Main --> RAuth & REvt & RCk & RTok
    RAuth --> SAuth
    RCk --> STok & SStor
    REvt --> STok
    RTok --> SWlt
    SAuth --> PG
    RAuth --> PG
    REvt --> PG
    RCk --> PG
    RTok --> PG
    SStor --> SB
    SSMS --> TW
    SWlt --> GW
```

## Deployment Topology (docker-compose)

```mermaid
flowchart LR
    DB[(postgres:15-alpine<br/>:5432<br/>init: supabase/schema.sql)]
    BE[backend<br/>uvicorn :8000<br/>hot-reload]
    FE[frontend<br/>node:20 vite dev :5173<br/>proxy /api -> backend]
    FE -->|HTTP /api| BE
    BE -->|asyncpg| DB
```

## Request Flow — Operator Check-in (digital, auto-position)

```mermaid
sequenceDiagram
    actor Op as Operator
    participant FE as CheckinPage
    participant QR as QRScanner
    participant API as client.ts
    participant BE as /api/checkin
    participant TS as token_service
    participant DB as PostgreSQL

    Op->>FE: Open /checkin
    FE->>API: GET /events + /events/{id}/next-slot
    API->>BE: HTTP w/ Bearer JWT
    BE->>DB: SELECT events, scan racks/checkins
    DB-->>BE: next free slot
    BE-->>FE: {rack_id,slot}
    Op->>QR: scan customer QR
    QR-->>FE: token code (DOT-XXXX)
    FE->>API: POST /checkin {token_code, auto_position:true}
    API->>BE: HTTP
    BE->>DB: SELECT token by code + selectinload(customer)
    BE->>DB: scan racks ordered, pick first free slot
    BE->>DB: INSERT checkin, UPDATE token.status='checked_in'
    DB-->>BE: commit (via get_db context)
    BE-->>FE: CheckinResponse {position, token, customer.phone_masked}
    FE->>FE: notifications.show + invalidate queries
```

## Request Flow — Public Reservation

```mermaid
sequenceDiagram
    actor C as Customer
    participant FE as EventPage
    participant BE as /api/events/{slug}/reserve
    participant TS as token_service
    participant DB as PostgreSQL
    participant TW as Twilio (TODO)

    C->>FE: GET /evento/{slug}
    FE->>BE: GET /events/{slug}/availability (no auth)
    BE->>DB: SELECT event + count(tokens in reserved/checked_in)
    BE-->>FE: availability + can_reserve
    C->>FE: submit phone/email
    FE->>BE: POST /events/{slug}/reserve
    BE->>TS: normalize_phone (E.164)
    BE->>DB: get_or_create_customer
    BE->>DB: check existing token for this customer+event
    BE->>TS: get_unique_token_code (DOT-XXXX, up to 10 tries)
    BE->>DB: INSERT token status='reserved'
    BE-->>FE: {code, qr_url, wallet_url, message_sent:false}
    Note over BE,TW: TODO — SMS send not wired
```

## Request Flow — Check-out

```mermaid
sequenceDiagram
    actor Op as Operator
    participant FE as CheckoutPage
    participant BE as /api/checkout
    participant DB as PostgreSQL

    Op->>FE: scan QR
    FE->>BE: POST /checkout {token_code}
    BE->>DB: SELECT Token w/ selectinload(checkin.rack, customer)
    alt token.status != 'checked_in'
        BE-->>FE: 400 "Token is not checked in"
    else ok
        BE->>DB: UPDATE checkin.checked_out_at, checked_out_by
        alt type == 'physical'
            BE->>DB: UPDATE token.status = 'available'  (reusable)
        else digital
            BE->>DB: UPDATE token.status = 'checked_out'
        end
        BE-->>FE: {position, checked_in_at, bike_photo_url, token_type}
    end
```
