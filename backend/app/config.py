import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "WealthPilot AI Core Backend"
    API_V1_STR: str = "/api/v1"
    
    # Security Configuration
    JWT_SECRET: str = os.getenv("JWT_SECRET", "wealthpilot_super_secret_jwt_sign_key_99238c8")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120 # 2 hours token expiry
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./wealthpilot_modular.db")
    
    class Config:
        case_sensitive = True

settings = Settings()
