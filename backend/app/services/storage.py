"""
Dottò - Storage Service (Supabase)
"""
import base64
import io
from typing import Optional
from uuid import uuid4

from PIL import Image

from app.config import get_settings

settings = get_settings()


async def upload_bike_photo(
    photo_base64: str,
    token_code: str,
) -> Optional[str]:
    """
    Upload a bike photo to Supabase Storage.
    
    Args:
        photo_base64: Base64 encoded image data
        token_code: Token code for filename
    
    Returns:
        Public URL of the uploaded image, or None if failed
    """
    try:
        from supabase import create_client
        
        # Decode base64
        # Remove data URL prefix if present
        if "," in photo_base64:
            photo_base64 = photo_base64.split(",")[1]
        
        image_data = base64.b64decode(photo_base64)
        
        # Open and resize image
        image = Image.open(io.BytesIO(image_data))
        
        # Resize to max 1200px on longest side
        max_size = 1200
        if max(image.size) > max_size:
            ratio = max_size / max(image.size)
            new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        # Convert to JPEG
        output = io.BytesIO()
        image.convert("RGB").save(output, format="JPEG", quality=85)
        output.seek(0)
        
        # Upload to Supabase
        supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)
        
        filename = f"bikes/{token_code}/{uuid4().hex}.jpg"
        
        result = supabase.storage.from_("bike-photos").upload(
            filename,
            output.getvalue(),
            file_options={"content-type": "image/jpeg"},
        )
        
        if result.path:
            # Get public URL
            public_url = supabase.storage.from_("bike-photos").get_public_url(filename)
            return public_url
        
        return None
        
    except ImportError:
        print("[Storage] Supabase not available, skipping upload")
        return None
    except Exception as e:
        print(f"[Storage] Failed to upload photo: {e}")
        return None


async def delete_bike_photo(photo_url: str) -> bool:
    """Delete a bike photo from storage."""
    try:
        from supabase import create_client
        
        supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)
        
        # Extract path from URL
        # URL format: https://.../storage/v1/object/public/bike-photos/path
        path = photo_url.split("/bike-photos/")[-1]
        
        supabase.storage.from_("bike-photos").remove([path])
        return True
        
    except Exception as e:
        print(f"[Storage] Failed to delete photo: {e}")
        return False

