from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_ID: str
    REGION: str
    
    # Database (AlloyDB)
    DB_HOST: str      # Injected by Terraform
    DB_USER: str = "postgres"
    DB_PASSWORD: str  # Injected from Secret Manager
    DB_NAME: str = "vector_store" # You must create this DB manually or via init script
    
    # Firestore
    FIRESTORE_COLLECTION: str = "chat_history"

    class Config:
        env_file = ".env"

settings = Settings()