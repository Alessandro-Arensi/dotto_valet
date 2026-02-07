# Workflow branch: develop → main

- **`develop`**: ambiente di sviluppo. Tutte le feature e il lavoro quotidiano avvengono qui.
- **`main`**: produzione. Contiene solo release stabili; da qui si generano gli artifact di produzione.

## Flusso

1. Lavora sempre su **develop** (`git checkout develop`).
2. Commit e push su `develop` durante lo sviluppo.
3. Quando hai una release robusta e testata:
   - Merge (o PR) da `develop` → `main`.
   - Su `main`: tag di versione (es. `v1.0.0`) e build dell’artifact di produzione (Docker image, bundle frontend, ecc.).

## Comandi utili

```bash
# Lavorare su develop
git checkout develop

# Creare un branch feature (opzionale)
git checkout -b feature/nome-feature develop

# Preparare una release: merge develop → main
git checkout main
git merge develop --no-ff -m "Release x.y.z"
git tag vx.y.z
git push origin main --tags
```

## Nota

Non fare commit diretti su `main` per lo sviluppo; usa sempre `develop` (o branch derivati da `develop`).
