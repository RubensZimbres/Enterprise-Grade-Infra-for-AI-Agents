from fastapi import Header, HTTPException, Depends
from google.oauth2 import id_token
from google.auth.transport import requests
import logging

logger = logging.getLogger(__name__)

def get_current_user(authorization: str = Header(None)):
    """
    Validates the OIDC ID Token sent in the Authorization header.
    Returns the user's email if valid.
    """
    if not authorization or not authorization.startswith("Bearer "):
        logger.warning("Missing or invalid Authorization header")
        raise HTTPException(status_code=401, detail="Unauthorized: Missing Token")

    token = authorization.split(" ")[1]
    
    try:
        # Verify the ID token using Google's public keys
        # The 'audience' should ideally be the Backend URL, 
        # but in many internal Cloud Run setups, it's the Client ID or URL.
        # We use a generic check here, but in production, specify the exact audience.
        id_info = id_token.verify_oauth2_token(token, requests.Request())

        # Extract user info
        user_email = id_info.get("email")
        if not user_email:
            raise HTTPException(status_code=401, detail="Unauthorized: Email not found in token")
            
        return user_email

    except Exception as e:
        logger.error(f"Token validation error: {e}")
        raise HTTPException(status_code=401, detail=f"Unauthorized: Invalid Token")
