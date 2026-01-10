"""
FastAPI application entry point for KingSick backend.

Provides the main FastAPI application instance with CORS configuration,
health check endpoints, and API router mounting.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.api_keys import router as api_keys_router
from app.api.auth import router as auth_router
from app.api.indicators import router as indicators_router
from app.api.invitations import router as invitations_router
from app.api.positions import router as positions_router
from app.api.signals import router as signals_router
from app.api.stocks import router as stocks_router
from app.api.trades import router as trades_router
from app.api.trading import router as trading_router
from app.api.users import router as users_router
from app.api.watchlist import router as watchlist_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="KingSick API",
    description="AI-powered automated trading system for Korean stock market",
    version="1.0.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    """
    Root endpoint with welcome message.

    Returns:
        dict: Welcome message and API information.
    """
    return {
        "message": "Welcome to KingSick API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check() -> dict[str, str]:
    """
    Health check endpoint for monitoring and load balancers.

    Returns:
        dict: Health status and application information.
    """
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
    }


# Include API routers with /api/v1 prefix
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(invitations_router, prefix="/api/v1")
app.include_router(api_keys_router, prefix="/api/v1")
app.include_router(indicators_router, prefix="/api/v1")
app.include_router(positions_router, prefix="/api/v1")
app.include_router(signals_router, prefix="/api/v1")
app.include_router(trades_router, prefix="/api/v1")
app.include_router(trading_router, prefix="/api/v1")
app.include_router(watchlist_router, prefix="/api/v1")
app.include_router(stocks_router, prefix="/api/v1")
