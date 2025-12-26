import os
import asyncio
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_postgres import PGVector
from config import settings

"""
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; -- Often needed for ID generation

./cloud-sql-proxy --private-ip projects/YOUR_PROJECT/locations/YOUR_REGION/clusters/YOUR_CLUSTER/instances/YOUR_INSTANCE
"""



# --- CONFIGURATION ---
DATA_PATH = "./data"
CHUNK_SIZE = 1000  # Tokens/Characters per chunk. Tunable parameter.
CHUNK_OVERLAP = 200 # Critical for keeping context across boundaries.

async def ingest_data():
    print(f"🚀 Starting Ingestion Pipeline for Project: {settings.PROJECT_ID}")
    
    # 1. Load Documents
    if not os.path.exists(DATA_PATH):
        print(f"❌ Error: Data directory '{DATA_PATH}' not found.")
        return

    print("📂 Loading documents...")
    # Smart loader that handles PDFs and TXT files automatically
    loader = DirectoryLoader(
        DATA_PATH, 
        glob="**/*.pdf", # Change to "**/*" for all files
        loader_cls=PyPDFLoader,
        show_progress=True
    )
    raw_docs = loader.load()
    
    if not raw_docs:
        print("⚠️  No documents found. Exiting.")
        return

    print(f"✅ Loaded {len(raw_docs)} documents.")

    # 2. Split Text (The Art of Chunking)
    print("✂️  Splitting documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""] # Try to split by paragraph first
    )
    
    chunks = text_splitter.split_documents(raw_docs)
    print(f"🧩 Generated {len(chunks)} chunks.")

    # 3. Connect to AlloyDB
    print("🔌 Connecting to AlloyDB...")
    embeddings = VertexAIEmbeddings(model_name="textembedding-gecko@003")
    
    connection_string = f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:5432/{settings.DB_NAME}"
    
    # Note: We use 'pre_delete_collection=True' to wipe old data for a clean slate.
    # In a real production incremental update, you would NOT do this.
    print(f"💾 Ingesting into table '{settings.DB_NAME}'...")
    
    vector_store = PGVector(
        embeddings=embeddings,
        collection_name="knowledge_base",
        connection=connection_string,
        use_jsonb=True,
    )

    # 4. Upsert Data
    # We do this in batches implicitly handled by LangChain, but you can force batching if needed.
    await vector_store.add_documents(chunks)
    
    print("🎉 Ingestion Complete! Your agent now has a brain.")

if __name__ == "__main__":
    # Ensure the async loop runs
    asyncio.run(ingest_data())