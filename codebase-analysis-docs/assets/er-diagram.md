# Entity-Relationship Diagram — Dottò

Defined in [db/schema.sql](../../db/schema.sql) and mirrored in SQLAlchemy [backend/app/models/](../../backend/app/models/).

```mermaid
erDiagram
    EVENTS ||--o{ RACKS : "has"
    EVENTS ||--o{ TOKENS : "sells"
    EVENTS ||--o{ CHECKINS : "hosts"
    EVENTS ||--o{ ACTIVITY_LOGS : "logs"
    CUSTOMERS ||--o{ TOKENS : "owns"
    TOKENS ||--o| CHECKINS : "has one (unique token_id)"
    RACKS ||--o{ CHECKINS : "occupies"
    OPERATORS ||--o{ CHECKINS : "checked_in_by / checked_out_by"
    OPERATORS ||--o{ ACTIVITY_LOGS : "actor"

    EVENTS {
        uuid id PK
        varchar name
        varchar slug UK
        text description
        varchar location
        point location_coords
        timestamptz start_date
        timestamptz end_date
        timestamptz checkin_opens_at
        int total_capacity
        int fast_mode_threshold "default 80"
        bool is_active
        timestamptz created_at
        timestamptz updated_at
    }

    RACKS {
        uuid id PK
        uuid event_id FK "ON DELETE CASCADE"
        int rack_number
        int slots "default 12"
        varchar label
    }

    OPERATORS {
        uuid id PK
        varchar name
        varchar phone
        varchar email
        varchar pin_hash "bcrypt"
        bool is_admin
        bool is_active
        timestamptz created_at
    }

    CUSTOMERS {
        uuid id PK
        varchar phone
        varchar phone_normalized UK "E.164"
        varchar email
        bool newsletter_opt_in
        timestamptz created_at
    }

    TOKENS {
        uuid id PK
        varchar code UK "DOT-XXXX"
        varchar type "digital|physical"
        varchar status "available|reserved|checked_in|checked_out|expired|lost"
        uuid event_id FK
        uuid customer_id FK
        timestamptz reserved_at
        timestamptz expires_at
        timestamptz created_at
    }

    CHECKINS {
        uuid id PK
        uuid token_id FK,UK
        uuid event_id FK
        uuid rack_id FK
        int slot_number
        varchar bike_photo_url "required for physical"
        bool auto_positioned
        timestamptz checked_in_at
        timestamptz checked_out_at
        uuid checked_in_by FK
        uuid checked_out_by FK
        bool manual_override
        text override_reason
    }

    ACTIVITY_LOGS {
        uuid id PK
        uuid operator_id FK
        uuid event_id FK
        varchar action
        varchar entity_type
        uuid entity_id
        jsonb metadata
        inet ip_address
        text user_agent
        timestamptz created_at
    }
```

## Key Constraints & Indexes

| Table      | Constraint / Index                                         | Purpose                                               |
|------------|------------------------------------------------------------|-------------------------------------------------------|
| `events`   | `slug UNIQUE`                                              | Public URL path `/evento/{slug}`                      |
| `racks`    | `UNIQUE (event_id, rack_number)`                           | No duplicate rack numbering per event                 |
| `customers`| `UNIQUE (phone_normalized)`                                | One customer per E.164 number                         |
| `tokens`   | `UNIQUE (code)`, `CHECK type IN (...)`, `CHECK status IN (...)` | Token identity + state machine                  |
| `tokens`   | `idx_tokens_customer_event`, `idx_tokens_status`           | Recovery lookups, status filters                      |
| `checkins` | `token_id UNIQUE`                                          | One checkin row per token (lifetime); re-checkins require new token for digital type |
| `checkins` | `UNIQUE (rack_id, slot_number, checked_out_at)`            | Allows slot reuse: multiple rows may share slot, but only one with `checked_out_at IS NULL` |
| `checkins` | `idx_checkins_active` (partial `WHERE checked_out_at IS NULL`) | Fast "active parked bikes" queries               |
| `activity_logs` | `idx_logs_event (event_id, created_at DESC)`          | Timeline queries                                      |

## Views & Functions

- `VIEW event_availability` — computes `occupied/available/occupancy_percent` per active event.
- `VIEW available_slots` — `CROSS JOIN generate_series(1, r.slots)` minus occupied.
- `FUNCTION get_next_available_slot(event_id)` — returns first free slot ordered by `rack_number, slot_number`.
- `FUNCTION generate_token_code()` — DB-side DOT-XXXX generator (unused by backend; backend reimplements in [token_service.py](../../backend/app/services/token_service.py)).

## Token State Machine

```mermaid
stateDiagram-v2
    [*] --> reserved: POST /events/{slug}/reserve (digital)
    [*] --> available: Physical token seed (manual)
    available --> checked_in: POST /checkin (physical path)
    reserved --> checked_in: POST /checkin
    reserved --> expired: (no-show; NOT YET IMPLEMENTED)
    checked_in --> checked_out: POST /checkout (digital)
    checked_in --> available: POST /checkout (physical — reusable)
    checked_out --> [*]
    available --> lost: manual admin action (NOT IMPLEMENTED)
```
