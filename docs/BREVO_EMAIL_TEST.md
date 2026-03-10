# Brevo – Test email senza dominio verificato

Per testare l’invio email **senza** configurare il dominio (DNS/DKIM) puoi usare un **mittente verificato solo via email** (OTP). Le email possono finire in **spam**, ma l’invio funziona e puoi testare il flusso.

## Passi

1. **Accedi a Brevo**  
   https://app.brevo.com

2. **Aggiungi un mittente**  
   - Vai in **Settings** (ingranaggio) → **Senders & IP** → **Senders**  
   - Clicca **Add a sender**  
   - Inserisci un’email che controlli (es. la tua email personale `tua@live.com` o `tua@gmail.com`)  
   - Nome mittente: es. `Dottò`  
   - Salva

3. **Verifica il mittente con OTP**  
   - Brevo invia un codice a 6 cifre a quell’indirizzo  
   - Inserisci il codice nella schermata Brevo per completare la verifica  
   - Non serve configurare DNS o dominio

4. **Configura il progetto**  
   Nel `.env` imposta la **stessa email** usata come mittente:

   ```env
   BREVO_API_KEY=la_tua_api_key
   BREVO_SENDER_EMAIL=tua@live.com
   BREVO_SENDER_NAME=Dottò
   ```

5. **Test**  
   Crea una prenotazione (o usa l’endpoint che invia email). Controlla la casella (e la cartella **spam**) del destinatario.

## Produzione

In produzione conviene:
- Verificare il **dominio** (es. `dotto.bike`) in Brevo e configurare DKIM/SPF  
- Usare un mittente tipo `noreply@dotto.bike` per ridurre il rischio che le email finiscano in spam.
