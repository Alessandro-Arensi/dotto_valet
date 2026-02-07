// Migration: crea le collection events, racks, operators, tokens per Dottò
// Eseguita automaticamente al primo avvio di PocketBase

migrate(
  (app) => {
    // --- 1. Collection: events ---
    const events = new Collection({
      type: "base",
      name: "events",
      listRule: "@request.auth.id != '' || is_active = true",
      viewRule: "@request.auth.id != '' || is_active = true",
      createRule: "@request.auth.id != ''",
      updateRule: "@request.auth.id != ''",
      deleteRule: "@request.auth.id != ''",
      fields: [
        { name: "name", type: "text", required: true },
        { name: "slug", type: "text", required: true },
        { name: "location", type: "text" },
        { name: "start_date", type: "date", required: true },
        { name: "end_date", type: "date" },
        { name: "total_capacity", type: "number", required: true, min: 0 },
        { name: "slots_available", type: "number", required: true, min: 0 },
        { name: "checkin_opens_at", type: "date" },
        { name: "is_active", type: "bool", required: true },
      ],
      indexes: ["CREATE UNIQUE INDEX idx_events_slug ON events (slug)"],
    });
    app.save(events);

    const eventsId = app.findCollectionByNameOrId("events").id;

    // --- 2. Collection: racks ---
    const racks = new Collection({
      type: "base",
      name: "racks",
      listRule: "@request.auth.id != ''",
      viewRule: "@request.auth.id != ''",
      createRule: "@request.auth.id != ''",
      updateRule: "@request.auth.id != ''",
      deleteRule: "@request.auth.id != ''",
      fields: [
        { name: "event", type: "relation", required: true, maxSelect: 1, collectionId: eventsId, cascadeDelete: true },
        { name: "rack_number", type: "number", required: true, min: 0 },
        { name: "slots", type: "number", required: true, min: 0 },
        { name: "label", type: "text" },
      ],
      indexes: ["CREATE UNIQUE INDEX idx_racks_event_number ON racks (event, rack_number)"],
    });
    app.save(racks);

    const racksId = app.findCollectionByNameOrId("racks").id;

    // --- 3. Collection: operators (auth) ---
    const operators = new Collection({
      type: "auth",
      name: "operators",
      listRule: "@request.auth.id != ''",
      viewRule: "@request.auth.id != ''",
      createRule: "",
      updateRule: "id = @request.auth.id",
      deleteRule: "",
      fields: [
        { name: "name", type: "text", required: true },
        { name: "is_admin", type: "bool", required: true },
      ],
    });
    app.save(operators);

    // --- 4. Collection: tokens ---
    // Creazione pubblica (prenotazione); list/view/update/delete solo operatori; un token per email per evento in hook
    const tokens = new Collection({
      type: "base",
      name: "tokens",
      listRule: "@request.auth.id != ''",
      viewRule: "@request.auth.id != ''",
      createRule: null,
      updateRule: "@request.auth.id != ''",
      deleteRule: "@request.auth.id != ''",
      fields: [
        { name: "event", type: "relation", required: true, maxSelect: 1, collectionId: eventsId, cascadeDelete: true },
        { name: "email", type: "email", required: true },
        { name: "phone", type: "text" },
        { name: "token_code", type: "text", required: true },
        { name: "token_type", type: "select", required: true, values: ["digital", "physical"] },
        { name: "status", type: "select", required: true, values: ["pending", "checked_in", "checked_out"] },
        { name: "rack", type: "relation", required: false, maxSelect: 1, collectionId: racksId },
        { name: "slot_num", type: "number", min: 0 },
        { name: "photo", type: "file", required: false, maxSelect: 1, maxSize: 5242880 },
        { name: "newsletter_opt_in", type: "bool", required: true },
        { name: "whatsapp_sent", type: "bool", required: true },
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_tokens_token_code ON tokens (token_code)",
        "CREATE UNIQUE INDEX idx_tokens_event_email ON tokens (event, email)",
      ],
    });
    app.save(tokens);
  },
  (app) => {
    // Down: elimina in ordine inverso per dipendenze
    try {
      const tokens = app.findCollectionByNameOrId("tokens");
      app.delete(tokens);
    } catch (e) {}
    try {
      const operators = app.findCollectionByNameOrId("operators");
      app.delete(operators);
    } catch (e) {}
    try {
      const racks = app.findCollectionByNameOrId("racks");
      app.delete(racks);
    } catch (e) {}
    try {
      const events = app.findCollectionByNameOrId("events");
      app.delete(events);
    } catch (e) {}
  }
);
