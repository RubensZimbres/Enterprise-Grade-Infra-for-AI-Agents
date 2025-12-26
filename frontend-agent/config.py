import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # The URL of your Backend Agent (Cloud Run Service)
    # Default is localhost for testing, but OVERRIDE this in Production!
    BACKEND_URL: str = "http://localhost:8080" 
    
    class Config:
        env_file = ".env"

settings = Settings()