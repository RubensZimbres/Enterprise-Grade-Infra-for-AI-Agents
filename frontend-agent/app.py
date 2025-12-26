import streamlit as st
import requests
import google.auth.transport.requests
import google.oauth2.id_token
from config import settings
import uuid


# --- Page Config ---
st.set_page_config(
    page_title="Enterprise AI Agent",
    page_icon="🛡️",
    layout="centered"
)

st.title("🛡️ Enterprise RAG Agent")
st.markdown(f"*Connected to Backend: `{settings.BACKEND_URL}`*")

# HELPER FUNCTION: Get the ID Token
def get_id_token(url):
    """
    Generates an OIDC ID Token for the target URL.
    This works automatically on Cloud Run using the assigned Service Account.
    """
    # Create a request object for the auth library
    auth_req = google.auth.transport.requests.Request()
    
    # Fetch the token specifically for the audience (the Backend URL)
    try:
        id_token = google.oauth2.id_token.fetch_id_token(auth_req, url)
        return id_token
    except Exception as e:
        # Fallback for local testing (if not authenticated)
        print(f"Auth Error: {e}")
        return None

# --- 1. Session Management ---
if "session_id" not in st.session_state:
    # Generate a unique session ID for this user browser tab
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 2. Display Chat History ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 3. Handle User Input ---
if prompt := st.chat_input("Ask me anything about the internal docs..."):
    # A. Display User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # B. Call Backend API
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            with st.spinner("Consulting Neural Core..."):
                payload = {
                    "session_id": st.session_state.session_id,
                    "message": prompt
                }
                
                # 1. GENERATE TOKEN
                # We need the base URL (without /chat) for the audience, 
                # or the exact URL depending on how strict the backend is.
                # Usually, the Audience is the ROOT URL of the service.
                token = get_id_token(settings.BACKEND_URL)
                
                if not token:
                    st.error("Authentication Failed: Could not generate ID Token.")
                    st.stop()
                
                headers = {}
                headers["Authorization"] = f"Bearer {token}"
                
                # 2. SEND AUTHENTICATED REQUEST
                response = requests.post(
                    f"{settings.BACKEND_URL}/chat",
                    json=payload,
                    headers=headers, # <--- THE KEY
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    full_response = data.get("response", "Error: Empty response.")
                else:
                    full_response = f"⚠️ Error {response.status_code}: {response.text}"
                    
        except requests.exceptions.ConnectionError:
            full_response = "❌ Connection Failed. Is the Backend running?"
        except Exception as e:
            full_response = f"❌ An error occurred: {str(e)}"

        # C. Render Response
        message_placeholder.markdown(full_response)
        
        # D. Save to Local State
        st.session_state.messages.append({"role": "assistant", "content": full_response})