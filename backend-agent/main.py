import logging
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from chains.rag_chain import protected_chain_invoke

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Enterprise AI Agent", version="1.0.0")

class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(..., max_length=10000) # Limit to 10k chars (DoS Protection)

class ChatResponse(BaseModel):
    response: str

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Main entry point for the Frontend Agent.
    Handles RAG, Memory, and DLP.
    """
    try:
        # Invoke the chain with guardrails
        # Note: In production, you should use .astream() for streaming responses
        response_text = await run_in_threadpool(protected_chain_invoke, request.message, request.session_id)
        
        return ChatResponse(response=response_text)
    
    except Exception as e:
        # Log the stack trace securely (Hidden from user)
        logger.error("Error processing request", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Processing Error")

if __name__ == "__main__":
    import uvicorn
    # Listen on 0.0.0.0 because we are inside a container
    uvicorn.run(app, host="0.0.0.0", port=8080)