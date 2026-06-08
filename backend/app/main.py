import os
import sys

# Path patch to support running this file directly or as a module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.auth.router import router as auth_router
from app.portfolios.router import router as portfolios_router
from app.rebalancing.router import router as rebalancing_router
from app.audit.router import router as audit_router
from app.seeding import seed_database

# Make sure all models are imported so SQLAlchemy registers them with metadata
from app.auth.models import User
from app.portfolios.models import RiskCategory, Portfolio, Asset, PortfolioHolding, TaxLot
from app.rebalancing.models import RebalanceProposal, ProposedTrade
from app.audit.models import AuditLog

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    # Setup database metadata schemas
    Base.metadata.create_all(bind=engine)
    # Seed 5,000 portfolios, target parameters, and a default administrative account
    seed_database(5000)

# Register routers under prefix
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(portfolios_router, prefix=settings.API_V1_STR)
app.include_router(rebalancing_router, prefix=settings.API_V1_STR)
app.include_router(audit_router, prefix=settings.API_V1_STR)

@app.get("/")
def health_check():
    return {"status": "HEALTHY", "service": settings.PROJECT_NAME}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
