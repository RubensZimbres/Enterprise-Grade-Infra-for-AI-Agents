from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_ID: str
    REGION: str
    
    # Database (AlloyDB)
    DB_HOST: str      # Injected by Terraform
    DB_USER: str = "postgres"
    DB_PASSWORD: str  # Injected from Secret Manager env var
    DB_NAME: str = "postgres" 
    
    # Firestore
    FIRESTORE_COLLECTION: str = "chat_history"

    class Config:
        # No env_file for production as secrets are injected as env vars
        pass

settings = Settings()