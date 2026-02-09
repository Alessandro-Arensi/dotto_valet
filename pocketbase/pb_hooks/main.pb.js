// Dottò – PocketBase hooks: tokens (validazione foto, decremento slot)
// File caricato in ordine alfabetico da pb_hooks/*.pb.js

// --- 1. Creazione token: foto obbligatoria per token fisici ---
onRecordCreateRequest((e) => {
  if (e.collection.name !== "tokens") {
    e.next();
    return;
  }
  try {
    if (e.record.get("token_type") === "physical") {
      var photo = e.record.get("photo");
      if (!photo || photo === "" || photo === null) {
        throw new BadRequestError("Foto bici obbligatoria per token fisici");
      }
    }
  } catch (err) {
    // Se è il nostro BadRequestError per foto mancante, rilancialo
    if (err && err.message && err.message.indexOf("Foto") >= 0) {
      throw err;
    }
    // Altrimenti ignora altri errori (es. campo photo non presente per token digital)
  }
  e.next();
}, "tokens");

// --- 2. Dopo creazione token: se status = checked_in, decrementa slot evento ---
// NOTA: Qualsiasi hook che modifica altri record (eventi) causa 400, anche usando gli hook di modello
// (onRecordCreate, onRecordCreateExecute, onRecordAfterCreateSuccess) suggeriti per modifiche cross-collection.
// Il decremento slot verrà gestito nel backend FastAPI quando viene chiamato l'endpoint di check-in.
// onRecordAfterCreateSuccess((e) => {
//   e.next();
// }, "tokens");

// --- 3. Update token: foto obbligatoria se physical; se status → checked_in, decrementa slot ---
onRecordUpdateRequest((e) => {
  if (e.collection.name !== "tokens") {
    e.next();
    return;
  }
  if (e.record.get("token_type") === "physical") {
    var photo = e.record.get("photo");
    if (!photo || photo === "") {
      throw new BadRequestError("Foto bici obbligatoria per token fisici");
    }
  }
  e.next();
}, "tokens");

// --- 4. Update token execute: decrementa slot quando status → checked_in ---
// NOTA: Come sopra, modificare altri record causa 400 - gestito nel backend FastAPI
// onRecordUpdateExecute((e) => {
//   e.next();
// }, "tokens");
