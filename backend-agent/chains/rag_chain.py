from langchain_google_vertexai import VertexAIEmbeddings, ChatVertexAI
from langchain_postgres import PGVector
from langchain_google_firestore import FirestoreChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import RunnableLambda
from config import settings
from .guardrails import deidentify_content

# 1. Setup Embeddings
embeddings = VertexAIEmbeddings(
    model_name="textembedding-gecko@003",
    project=settings.PROJECT_ID,
    location=settings.REGION
)

# 2. Setup AlloyDB Vector Store
# Connection string for psycopg (Sync)
connection_string = f"postgresql+psycopg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:5432/{settings.DB_NAME}"

vector_store = PGVector(
    embeddings=embeddings,
    collection_name="knowledge_base",
    connection=connection_string,
    use_jsonb=True,
)

# 3. Setup LLM
llm = ChatVertexAI(
    model_name="gemini-pro",
    temperature=0.3,
    project=settings.PROJECT_ID,
    location=settings.REGION
)

# 4. Define the RAG Prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant. Use the context below to answer."),
    ("system", "Context: {context}"),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}"),
])

# 5. Build the Chain
def get_retriever():
    return vector_store.as_retriever(search_kwargs={"k": 5})

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# The Core Logic
rag_chain = (
    RunnableLambda(lambda x: x["question"])  # Extract question
    | {
        "context": get_retriever() | format_docs,
        "question": lambda x: x,
        "history": lambda x: x["history"] # Pass through history
    }
    | prompt
    | llm
)

# 6. Add Memory (Firestore)
def get_session_history(session_id: str):
    return FirestoreChatMessageHistory(
        session_id=session_id,
        collection=settings.FIRESTORE_COLLECTION,
        client=None # Uses default Google Auth credentials (Identity)
    )

conversational_rag_chain = RunnableWithMessageHistory(
    rag_chain,
    get_session_history,
    input_messages_key="question",
    history_messages_key="history",
)

# 7. Add Guardrails (DLP)
def protected_chain_invoke(input_text: str, session_id: str):
    # Step A: Sanitize Input
    safe_input = deidentify_content(input_text, settings.PROJECT_ID)
    
    # Step B: Run Chain
    response = conversational_rag_chain.invoke(
        {"question": safe_input},
        config={"configurable": {"session_id": session_id}}
    )
    
    # Step C: Sanitize Output
    safe_output = deidentify_content(response.content, settings.PROJECT_ID)
    return safe_output