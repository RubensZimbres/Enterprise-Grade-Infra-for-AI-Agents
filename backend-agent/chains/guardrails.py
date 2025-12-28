import re
import asyncio
from google.cloud import dlp_v2

dlp_client = dlp_v2.DlpServiceClient()

# Fast-path regex patterns for common PII
PII_PATTERNS = {
    "EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    "PHONE": r"(\+\d{1,2}\s?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}",
    "CREDIT_CARD": r"\b(?:\d[ -]*?){13,16}\b"
}

def has_potential_pii(content: str) -> bool:
    """Quick check for PII patterns using regex."""
    for pattern in PII_PATTERNS.values():
        if re.search(pattern, content):
            return True
    return False

def _dlp_request(content: str, project_id: str):
    """Internal synchronous function for the DLP API call."""
    parent = f"projects/{project_id}"
    info_types = [{"name": "EMAIL_ADDRESS"}, {"name": "PHONE_NUMBER"}, {"name": "CREDIT_CARD_NUMBER"}]
    inspect_config = {"info_types": info_types}
    deidentify_config = {
        "info_type_transformations": {
            "transformations": [
                {"primitive_transformation": {"replace_with_info_type_config": {}}}
            ]
        }
    }
    
    response = dlp_client.deidentify_content(
        request={
            "parent": parent,
            "deidentify_config": deidentify_config,
            "inspect_config": inspect_config,
            "item": {"value": content},
        }
    )
    return response.item.value

async def deidentify_content(content: str, project_id: str):
    """
    Asynchronously masks PII using Google Cloud DLP.
    Uses a regex fast-path and runs the API call in a separate thread.
    """
    if not content:
        return ""
    
    # Fast Path: If no common PII patterns are found, skip the API call
    if not has_potential_pii(content):
        return content
        
    try:
        # Run the synchronous DLP call in a thread pool
        return await asyncio.to_thread(_dlp_request, content, project_id)
    except Exception:
        # Fallback to a generic masking or return content if API fails 
        return "[PROTECTED CONTENT]"