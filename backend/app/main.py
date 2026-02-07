"""
Dottò - FastAPI Application
Sistema Valet Biciclette per Eventi
by Scintilla Cicloprogetti
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, checkin, events, tokens
from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print(f"🚲 Dottò API starting in {settings.environment} mode")
    yield
    # Shutdown
    print("🚲 Dottò API shutting down")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Sistema Valet Biciclette per Eventi - by Scintilla Cicloprogetti",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(events.router, prefix="/api/events", tags=["Events"])
app.include_router(checkin.router, prefix="/api", tags=["Check-in/out"])
app.include_router(tokens.router, prefix="/api/token", tags=["Tokens"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.debug else None,
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
