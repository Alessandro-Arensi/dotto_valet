"""
Dottò - SMS Service (Twilio)
"""
from typing import Optional

from app.config import get_settings

settings = get_settings()


async def send_sms(to: str, message: str) -> bool:
    """
    Send an SMS via Twilio.
    Returns True if sent successfully, False otherwise.
    """
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        print(f"[SMS] Twilio not configured. Would send to {to}: {message}")
        return False
    
    try:
        from twilio.rest import Client
        
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        
        message = client.messages.create(
            body=message,
            from_=settings.twilio_phone_number,
            to=to,
        )
        
        print(f"[SMS] Sent to {to}, SID: {message.sid}")
        return True
    except Exception as e:
        print(f"[SMS] Failed to send to {to}: {e}")
        return False


async def send_reservation_sms(
    phone: str,
    token_code: str,
    event_name: str,
    qr_url: str,
) -> bool:
    """Send reservation confirmation SMS."""
    message = f"""🚲 Dottò - Prenotazione confermata!

Evento: {event_name}
Token: {token_code}

📱 Il tuo QR: {qr_url}

Mostra questo QR all'ingresso con la tua bici.
"""
    return await send_sms(phone, message)


async def send_checkin_sms(
    phone: str,
    token_code: str,
    position: str,
    qr_url: str,
) -> bool:
    """Send check-in confirmation SMS."""
    message = f"""🚲 Dottò - Check-in completato!

Token: {token_code}
Posizione: {position}

📱 Per ritiro: {qr_url}

Mostra questo QR per ritirare la tua bici.
"""
    return await send_sms(phone, message)


async def send_token_recovery_sms(
    phone: str,
    token_code: str,
    qr_url: str,
) -> bool:
    """Send token recovery SMS."""
    message = f"""🚲 Dottò - Recupero Token

Token: {token_code}
📱 Il tuo QR: {qr_url}

Mostra questo QR per ritirare la tua bici.
"""
    return await send_sms(phone, message)

