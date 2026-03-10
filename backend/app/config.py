"""
Dottò - Application Configuration
"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    app_name: str = "Dottò API"
    app_url: str = "https://dotto.bike"
    environment: str = "development"
    debug: bool = True

    # Database
    database_url: str

    # Supabase (optional in sviluppo: default vuoti per evitare errori se non configurato)
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480  # 8 hours

    # Twilio SMS
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # Brevo Email
    brevo_api_key: str = ""
    brevo_sender_email: str = "noreply@dotto.bike"
    brevo_sender_name: str = "Dottò"

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        # In sviluppo leggiamo il file .env dalla root del progetto
        # (una directory sopra backend/), così non serve duplicarlo.
        env_file = "../.env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
