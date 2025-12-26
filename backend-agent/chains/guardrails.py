from google.cloud import dlp_v2

dlp_client = dlp_v2.DlpServiceClient()

def deidentify_content(content: str, project_id: str):
    """
    Uses Google Cloud DLP to mask PII (Email, Phone, Credit Card)
    before sending to LLM or returning to user.
    """
    if not content:
        return ""
        
    parent = f"projects/{project_id}"
    
    # Configure what to look for
    info_types = [{"name": "EMAIL_ADDRESS"}, {"name": "PHONE_NUMBER"}, {"name": "CREDIT_CARD_NUMBER"}]
    
    inspect_config = {"info_types": info_types}
    
    # Configure how to mask it
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