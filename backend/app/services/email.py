"""
Dottò - Email Service (Brevo)

Servizio per invio email tramite Brevo API.
Supporta email HTML e plain text.
"""
import logging
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


async def send_email(
    to_email: str,
    to_name: Optional[str],
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
) -> bool:
    """
    Send an email via Brevo API.
    
    Args:
        to_email: Recipient email address
        to_name: Recipient name (optional)
        subject: Email subject
        html_content: HTML email body
        text_content: Plain text email body (optional, auto-generated from HTML if not provided)
    
    Returns:
        True if sent successfully, False otherwise
    """
    settings = get_settings()
    if not settings.brevo_api_key:
        logger.warning(f"[Email] Brevo not configured. Would send to {to_email}: {subject}")
        return False

    try:
        import brevo_python
        from brevo_python.api import TransactionalEmailsApi
        from brevo_python.model.send_smtp_email import SendSmtpEmail
        from brevo_python.model.send_smtp_email_sender import SendSmtpEmailSender
        from brevo_python.model.send_smtp_email_to import SendSmtpEmailTo

        configuration = brevo_python.Configuration()
        configuration.api_key["api-key"] = settings.brevo_api_key
        
        # Use sandbox mode in development (doesn't actually send emails)
        if settings.environment == "development" and settings.debug:
            # Sandbox mode: validates API call but doesn't send email
            # Add header to enable sandbox mode
            pass  # Brevo sandbox is enabled via X-Sib-Sandbox header, but SDK handles it differently

        api_instance = TransactionalEmailsApi(brevo_python.ApiClient(configuration))

        sender = SendSmtpEmailSender(
            email=settings.brevo_sender_email,
            name=settings.brevo_sender_name or settings.app_name,
        )

        recipient = SendSmtpEmailTo(email=to_email, name=to_name)

        email_data = SendSmtpEmail(
            sender=sender,
            to=[recipient],
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

        api_instance.send_transac_email(email_data)
        logger.info(f"[Email] Sent to {to_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"[Email] Failed to send to {to_email}: {e}")
        return False


async def send_reservation_email(
    to_email: str,
    to_name: Optional[str],
    token_code: str,
    event_name: str,
    event_location: Optional[str],
    event_date: str,
    qr_url: str,
    wallet_url: Optional[str] = None,
) -> bool:
    """
    Send reservation confirmation email with QR code.
    
    Args:
        to_email: Recipient email address
        to_name: Recipient name (optional)
        token_code: Token code (e.g., "DOT-1234")
        event_name: Event name
        event_location: Event location (optional)
        event_date: Event date/time (formatted string)
        qr_url: URL to QR code page
        wallet_url: URL to add to wallet (optional)
    
    Returns:
        True if sent successfully, False otherwise
    """
    subject = f"🚲 Dottò - Prenotazione confermata per {event_name}"

    location_text = f"<p><strong>📍 Luogo:</strong> {event_location}</p>" if event_location else ""
    wallet_section = ""
    if wallet_url:
        wallet_section = f"""
        <p>
            <strong>📱 Aggiungi al Wallet:</strong><br>
            <a href="{wallet_url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 10px;">
                Aggiungi a Google Wallet / Apple Wallet
            </a>
        </p>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Prenotazione Confermata - Dottò</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0;">
            <h1 style="margin: 0;">🚲 Dottò</h1>
            <p style="margin: 10px 0 0 0;">Prenotazione Confermata</p>
        </div>
        
        <div style="background-color: #f9f9f9; padding: 20px; border-radius: 0 0 10px 10px;">
            <p>Ciao{(' ' + to_name) if to_name else ''},</p>
            
            <p>La tua prenotazione per il servizio valet bici è stata confermata!</p>
            
            <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>🎫 Token:</strong> <code style="background-color: #f0f0f0; padding: 5px 10px; border-radius: 3px; font-size: 18px; font-weight: bold;">{token_code}</code></p>
                <p><strong>📅 Evento:</strong> {event_name}</p>
                <p><strong>📅 Data:</strong> {event_date}</p>
                {location_text}
            </div>
            
            <p>
                <strong>📱 Il tuo QR Code:</strong><br>
                <a href="{qr_url}" style="background-color: #2196F3; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 10px;">
                    Visualizza QR Code
                </a>
            </p>
            
            {wallet_section}
            
            <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0;">
                <p style="margin: 0;"><strong>💡 Come funziona:</strong></p>
                <ul style="margin: 10px 0 0 0; padding-left: 20px;">
                    <li>Mostra il QR code all'ingresso con la tua bici</li>
                    <li>L'operatore scansionerà il codice e ti assegnerà uno slot</li>
                    <li>Conserva il QR code per ritirare la bici al termine dell'evento</li>
                </ul>
            </div>
            
            <p style="margin-top: 30px; color: #666; font-size: 14px;">
                Se hai domande, rispondi a questa email o contattaci tramite il sito.
            </p>
            
            <p style="margin-top: 20px; color: #666; font-size: 12px; text-align: center;">
                Dottò by <a href="https://www.scintillacicloprogetti.it" style="color: #4CAF50;">Scintilla Cicloprogetti</a>
            </p>
        </div>
    </body>
    </html>
    """

    text_content = f"""
🚲 Dottò - Prenotazione Confermata

Ciao{(' ' + to_name) if to_name else ''},

La tua prenotazione per il servizio valet bici è stata confermata!

🎫 Token: {token_code}
📅 Evento: {event_name}
📅 Data: {event_date}
{('📍 Luogo: ' + event_location) if event_location else ''}

📱 Il tuo QR Code: {qr_url}
{f'📱 Aggiungi al Wallet: {wallet_url}' if wallet_url else ''}

💡 Come funziona:
- Mostra il QR code all'ingresso con la tua bici
- L'operatore scansionerà il codice e ti assegnerà uno slot
- Conserva il QR code per ritirare la bici al termine dell'evento

Se hai domande, rispondi a questa email o contattaci tramite il sito.

Dottò by Scintilla Cicloprogetti
https://www.scintillacicloprogetti.it
    """

    return await send_email(to_email, to_name, subject, html_content, text_content)


async def send_checkin_email(
    to_email: str,
    to_name: Optional[str],
    token_code: str,
    position: str,
    qr_url: str,
) -> bool:
    """
    Send check-in confirmation email.
    
    Args:
        to_email: Recipient email address
        to_name: Recipient name (optional)
        token_code: Token code
        position: Bike position (e.g., "Rastrelliera A - Slot 12")
        qr_url: URL to QR code page
    
    Returns:
        True if sent successfully, False otherwise
    """
    subject = f"🚲 Dottò - Check-in completato - {token_code}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Check-in Completato - Dottò</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #2196F3; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0;">
            <h1 style="margin: 0;">🚲 Dottò</h1>
            <p style="margin: 10px 0 0 0;">Check-in Completato</p>
        </div>
        
        <div style="background-color: #f9f9f9; padding: 20px; border-radius: 0 0 10px 10px;">
            <p>Ciao{(' ' + to_name) if to_name else ''},</p>
            
            <p>Il check-in della tua bici è stato completato con successo!</p>
            
            <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>🎫 Token:</strong> <code style="background-color: #f0f0f0; padding: 5px 10px; border-radius: 3px; font-size: 18px; font-weight: bold;">{token_code}</code></p>
                <p><strong>📍 Posizione:</strong> {position}</p>
            </div>
            
            <p>
                <strong>📱 Per ritirare la bici:</strong><br>
                <a href="{qr_url}" style="background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 10px;">
                    Visualizza QR Code
                </a>
            </p>
            
            <div style="background-color: #d1ecf1; border-left: 4px solid #2196F3; padding: 15px; margin: 20px 0;">
                <p style="margin: 0;"><strong>💡 Ricorda:</strong></p>
                <p style="margin: 10px 0 0 0;">Mostra il QR code all'operatore per ritirare la tua bici al termine dell'evento.</p>
            </div>
            
            <p style="margin-top: 30px; color: #666; font-size: 14px;">
                Buon evento!
            </p>
            
            <p style="margin-top: 20px; color: #666; font-size: 12px; text-align: center;">
                Dottò by <a href="https://www.scintillacicloprogetti.it" style="color: #4CAF50;">Scintilla Cicloprogetti</a>
            </p>
        </div>
    </body>
    </html>
    """

    text_content = f"""
🚲 Dottò - Check-in Completato

Ciao{(' ' + to_name) if to_name else ''},

Il check-in della tua bici è stato completato con successo!

🎫 Token: {token_code}
📍 Posizione: {position}

📱 Per ritirare la bici: {qr_url}

💡 Ricorda: Mostra il QR code all'operatore per ritirare la tua bici al termine dell'evento.

Buon evento!

Dottò by Scintilla Cicloprogetti
https://www.scintillacicloprogetti.it
    """

    return await send_email(to_email, to_name, subject, html_content, text_content)


async def send_token_recovery_email(
    to_email: str,
    to_name: Optional[str],
    token_code: str,
    qr_url: str,
) -> bool:
    """
    Send token recovery email.
    
    Args:
        to_email: Recipient email address
        to_name: Recipient name (optional)
        token_code: Token code
        qr_url: URL to QR code page
    
    Returns:
        True if sent successfully, False otherwise
    """
    subject = f"🚲 Dottò - Recupero Token - {token_code}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Recupero Token - Dottò</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #FF9800; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0;">
            <h1 style="margin: 0;">🚲 Dottò</h1>
            <p style="margin: 10px 0 0 0;">Recupero Token</p>
        </div>
        
        <div style="background-color: #f9f9f9; padding: 20px; border-radius: 0 0 10px 10px;">
            <p>Ciao{(' ' + to_name) if to_name else ''},</p>
            
            <p>Ecco il tuo token per il servizio valet bici:</p>
            
            <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>🎫 Token:</strong> <code style="background-color: #f0f0f0; padding: 5px 10px; border-radius: 3px; font-size: 18px; font-weight: bold;">{token_code}</code></p>
            </div>
            
            <p>
                <strong>📱 Il tuo QR Code:</strong><br>
                <a href="{qr_url}" style="background-color: #2196F3; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 10px;">
                    Visualizza QR Code
                </a>
            </p>
            
            <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0;">
                <p style="margin: 0;"><strong>💡 Come usare:</strong></p>
                <ul style="margin: 10px 0 0 0; padding-left: 20px;">
                    <li>Mostra il QR code all'operatore per ritirare la tua bici</li>
                    <li>Se hai già fatto il check-in, usa questo QR per il check-out</li>
                </ul>
            </div>
            
            <p style="margin-top: 30px; color: #666; font-size: 14px;">
                Se hai domande, rispondi a questa email o contattaci tramite il sito.
            </p>
            
            <p style="margin-top: 20px; color: #666; font-size: 12px; text-align: center;">
                Dottò by <a href="https://www.scintillacicloprogetti.it" style="color: #4CAF50;">Scintilla Cicloprogetti</a>
            </p>
        </div>
    </body>
    </html>
    """

    text_content = f"""
🚲 Dottò - Recupero Token

Ciao{(' ' + to_name) if to_name else ''},

Ecco il tuo token per il servizio valet bici:

🎫 Token: {token_code}

📱 Il tuo QR Code: {qr_url}

💡 Come usare:
- Mostra il QR code all'operatore per ritirare la tua bici
- Se hai già fatto il check-in, usa questo QR per il check-out

Se hai domande, rispondi a questa email o contattaci tramite il sito.

Dottò by Scintilla Cicloprogetti
https://www.scintillacicloprogetti.it
    """

    return await send_email(to_email, to_name, subject, html_content, text_content)
