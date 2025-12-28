from fastapi import Header, HTTPException, Depends, Request
from google.oauth2 import id_token
from google.auth.transport import requests
import logging
import os

logger = logging.getLogger(__name__)

def get_current_user(request: Request, authorization: str = Header(None)):
    """
    Validates the user identity.
    Checks for IAP header first (for production), then falls back to ID Token.
    """
    # 0. LOCAL DEVELOPMENT FALLBACK
    # If we are in local development and have a mock token, bypass Google Auth
    if os.getenv("DEBUG", "false").lower() == "true":
        if authorization == "Bearer MOCK_TOKEN":
            return "local-dev@example.com"

    # 1. Check for IAP Header (Injected by Google Identity-Aware Proxy)
    iap_email = request.headers.get("X-Goog-Authenticated-User-Email")
    if iap_email:
        # IAP prefix is usually "accounts.google.com:user@example.com"
        return iap_email.split(":")[-1]

    # 2. Fallback to OIDC ID Token validation
    if not authorization or not authorization.startswith("Bearer "):
        logger.warning("Missing or invalid Authorization header and no IAP header found")
        raise HTTPException(status_code=401, detail="Unauthorized: Missing Identity")

    token = authorization.split(" ")[1]
    
    try:
        id_info = id_token.verify_oauth2_token(token, requests.Request())
        user_email = id_info.get("email")
        if not user_email:
            raise HTTPException(status_code=401, detail="Unauthorized: Email not found in token")
            
        return user_email

    except Exception as e:
        logger.error(f"Token validation error: {e}")
        raise HTTPException(status_code=401, detail=f"Unauthorized: Invalid Token")
