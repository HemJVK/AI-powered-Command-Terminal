import sys
import os
from dotenv import load_dotenv
from langchain_milvus.vectorstores import Milvus
from langchain_core.documents import Document
# CORRECTED IMPORT: Use the local HuggingFaceEmbeddings model
from langchain_huggingface import HuggingFaceEmbeddings

# Add the parent directory to the path to import from 'agent'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent.dynamic_tools import load_system_command_tools

MILVUS_COLLECTION_NAME = "system_command_tools"

def main():
    """Ingests descriptions of the dynamically created tools into Milvus."""
    load_dotenv('../.env')

    tools = load_system_command_tools()

    if not tools:
        print("No tools were created. Aborting ingestion.")
        return

    documents = [
        Document(
            page_content=tool.description,
            metadata={"tool_name": tool.name}
        )
        for tool in tools
    ]
    
    print(f"\nPreparing to ingest {len(documents)} tool descriptions into Milvus...")

    try:
        # --- CORRECTED EMBEDDINGS LOGIC ---
        # Use a powerful, local, open-source sentence-transformer model.
        # This runs on your CPU and requires no API key.
        # The first time this runs, it will download the model (a few hundred MB).
        print("Initializing local embeddings model (may download on first run)...")
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        # --- END CORRECTION ---
        
        Milvus.from_documents(
            documents,
            embedding=embeddings,
            collection_name=MILVUS_COLLECTION_NAME,
            connection_args={"host": "localhost", "port": "19530"},
            drop_old=True
        )
        print(f"\n✅ Successfully ingested tools into Milvus collection '{MILVUS_COLLECTION_NAME}'.")
    except Exception as e:
        print(f"\n❌ Failed to ingest documents into Milvus: {e}")
        print("Please ensure your Milvus Docker container is running.")

if __name__ == "__main__":
    main()