-- =============================================
-- Dottò - Schema Database PostgreSQL
-- Sistema Valet Biciclette per Eventi
-- by Scintilla Cicloprogetti
-- =============================================

-- Estensioni
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =====================
-- TABELLA: events
-- =====================
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    location VARCHAR(255),
    location_coords POINT,  -- lat/lng opzionale
    
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE,
    checkin_opens_at TIMESTAMP WITH TIME ZONE,
    
    total_capacity INT NOT NULL,
    fast_mode_threshold INT DEFAULT 80,  -- % occupazione per suggerire fast mode
    
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================
-- TABELLA: racks (rastrelliere)
-- =====================
CREATE TABLE racks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    rack_number INT NOT NULL,
    slots INT DEFAULT 12,
    label VARCHAR(50),  -- es. "Ingresso Nord"
    
    UNIQUE(event_id, rack_number)
);

-- =====================
-- TABELLA: operators
-- =====================
CREATE TABLE operators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(255),
    pin_hash VARCHAR(255) NOT NULL,  -- login con PIN
    
    is_admin BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================
-- TABELLA: customers (dati minimi)
-- =====================
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),
    phone_normalized VARCHAR(20),  -- E.164 when phone present
    email VARCHAR(255),
    newsletter_opt_in BOOLEAN DEFAULT false,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_customers_name ON customers(last_name, first_name);
CREATE INDEX idx_customers_phone_normalized ON customers(phone_normalized);

-- =====================
-- TABELLA: tokens
-- =====================
CREATE TABLE tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(20) UNIQUE NOT NULL,  -- es. DOT-A7X9
    
    type VARCHAR(10) NOT NULL CHECK (type IN ('digital', 'physical')),
    status VARCHAR(15) DEFAULT 'reserved' CHECK (status IN (
        'available',    -- solo per token fisici non assegnati
        'reserved',     -- prenotato online, non ancora check-in
        'checked_in',   -- bici parcheggiata
        'checked_out',  -- bici ritirata
        'expired',      -- prenotazione scaduta (no-show)
        'lost'          -- token smarrito
    )),
    
    event_id UUID REFERENCES events(id),
    customer_id UUID REFERENCES customers(id),
    
    reserved_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indice per ricerca token per cliente/evento
CREATE INDEX idx_tokens_customer_event ON tokens(customer_id, event_id);
CREATE INDEX idx_tokens_status ON tokens(status);

-- =====================
-- TABELLA: checkins
-- =====================
CREATE TABLE checkins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_id UUID NOT NULL REFERENCES tokens(id),
    event_id UUID NOT NULL REFERENCES events(id),

    rack_id UUID NOT NULL REFERENCES racks(id),
    slot_number INT NOT NULL,

    -- Descrizione bici (opzionale, principalmente per token fisici come fallback identificazione in caso smarrimento gettone)
    bike_description VARCHAR(500),

    -- Flags modalità
    auto_positioned BOOLEAN DEFAULT false,
    
    -- Timestamps e operatori
    checked_in_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    checked_out_at TIMESTAMP WITH TIME ZONE,
    checked_in_by UUID REFERENCES operators(id),
    checked_out_by UUID REFERENCES operators(id),
    
    -- Override manuale (per casi perdita token fisico)
    manual_override BOOLEAN DEFAULT false,
    override_reason TEXT,
    
    UNIQUE(rack_id, slot_number, checked_out_at)  -- uno slot occupato alla volta
);

CREATE INDEX idx_checkins_active ON checkins(event_id) WHERE checked_out_at IS NULL;

-- =====================
-- TABELLA: slot_blocks
-- Uno slot può essere "bloccato" senza checkin (es. bici fuori posto,
-- bici cargo che occupa slot adiacenti, manutenzione rastrelliera).
-- L'auto-assign salta slot con block attivo (released_at IS NULL).
-- =====================
CREATE TABLE slot_blocks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rack_id UUID NOT NULL REFERENCES racks(id) ON DELETE CASCADE,
    slot_number INT NOT NULL,
    reason TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES operators(id),
    released_at TIMESTAMP WITH TIME ZONE,
    released_by UUID REFERENCES operators(id)
);

CREATE INDEX idx_slot_blocks_active ON slot_blocks(rack_id, slot_number) WHERE released_at IS NULL;

-- =====================
-- TABELLA: activity_logs
-- =====================
CREATE TABLE activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    operator_id UUID REFERENCES operators(id),
    event_id UUID REFERENCES events(id),
    
    action VARCHAR(50) NOT NULL,  -- 'checkin', 'checkout', 'override', 'token_lost', etc.
    entity_type VARCHAR(50),       -- 'token', 'checkin', etc.
    entity_id UUID,
    
    metadata JSONB,  -- dati aggiuntivi flessibili
    ip_address INET,
    user_agent TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_logs_event ON activity_logs(event_id, created_at DESC);

-- =====================
-- VISTE UTILI
-- =====================

-- Disponibilità evento
CREATE VIEW event_availability AS
SELECT 
    e.id as event_id,
    e.slug,
    e.name,
    e.total_capacity,
    e.start_date,
    e.checkin_opens_at,
    COUNT(t.id) FILTER (WHERE t.status IN ('reserved', 'checked_in')) as occupied,
    e.total_capacity - COUNT(t.id) FILTER (WHERE t.status IN ('reserved', 'checked_in')) as available,
    ROUND(
        COUNT(t.id) FILTER (WHERE t.status IN ('reserved', 'checked_in'))::numeric 
        / NULLIF(e.total_capacity, 0) * 100
    ) as occupancy_percent
FROM events e
LEFT JOIN tokens t ON t.event_id = e.id
WHERE e.is_active = true
GROUP BY e.id;

-- Slot disponibili per evento
CREATE VIEW available_slots AS
SELECT 
    r.event_id,
    r.id as rack_id,
    r.rack_number,
    r.label as rack_label,
    s.slot_number
FROM racks r
CROSS JOIN generate_series(1, r.slots) AS s(slot_number)
WHERE NOT EXISTS (
    SELECT 1 FROM checkins c 
    WHERE c.rack_id = r.id 
    AND c.slot_number = s.slot_number
    AND c.checked_out_at IS NULL
);

-- =====================
-- FUNZIONI
-- =====================

-- Prossimo slot disponibile
CREATE FUNCTION get_next_available_slot(p_event_id UUID)
RETURNS TABLE(rack_id UUID, rack_number INT, slot_number INT, rack_label VARCHAR) AS $$
BEGIN
    RETURN QUERY
    SELECT av.rack_id, av.rack_number, av.slot_number, av.rack_label
    FROM available_slots av
    WHERE av.event_id = p_event_id
    ORDER BY av.rack_number, av.slot_number
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Genera codice token univoco
CREATE FUNCTION generate_token_code() RETURNS VARCHAR(20) AS $$
DECLARE
    chars VARCHAR := 'ABCDEFGHJKMNPQRSTUVWXYZ23456789';  -- esclusi 0/O, 1/I/L
    result VARCHAR := 'DOT-';  -- Prefisso Dottò
    i INT;
BEGIN
    FOR i IN 1..4 LOOP
        result := result || substr(chars, floor(random() * length(chars) + 1)::int, 1);
    END LOOP;
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- =====================
-- DATI DI TEST (opzionale)
-- =====================

-- Admin operator default — login con phone=+39000000000, PIN=1234
-- Hash bcrypt valido per PIN '1234' (cambiare in produzione)
INSERT INTO operators (name, phone, pin_hash, is_admin) VALUES
('Admin', '+39000000000', '$2b$12$W9OZqn0DblDz9dfy.v77qu8ARRqmmfkeRTP0nbsg9fHYTxxtENy/C', true);

-- Inserisci un evento di test
INSERT INTO events (name, slug, location, start_date, end_date, checkin_opens_at, total_capacity) VALUES
('Evento Test', 'evento-test', 'Milano, Parco Sempione', NOW() + INTERVAL '1 day', NOW() + INTERVAL '2 days', NOW() + INTERVAL '1 day', 120);

-- Inserisci rastrelliere per l'evento di test
INSERT INTO racks (event_id, rack_number, slots, label)
SELECT 
    (SELECT id FROM events WHERE slug = 'evento-test'),
    n,
    12,
    'Rastrelliera ' || n
FROM generate_series(1, 10) AS n;


