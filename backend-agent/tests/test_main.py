def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_chat_endpoint_auth_required(client):
    # Without auth override, this should fail (assuming the real dependency checks a token)
    # The real dependency likely raises 403 or 401 if no token is present.
    # Based on main.py logic, it depends on get_current_user.
    response = client.post("/chat", json={"session_id": "123", "message": "hello"})
    # It might return 401/403, or 422 if validation fails first. 
    # Usually FastAPI returns 401 for missing auth if configured standardly, 
    # or 403 if token is invalid.
    assert response.status_code in [401, 403]

def test_chat_endpoint_success(client, mock_auth_user, mocker):
    # Mock the protected_chain_invoke to avoid hitting Vertex AI
    mocker.patch("main.protected_chain_invoke", return_value="Hello from Mock AI")
    
    response = client.post("/chat", json={"session_id": "123", "message": "hello"})
    assert response.status_code == 200
    assert response.json() == {"response": "Hello from Mock AI"}
