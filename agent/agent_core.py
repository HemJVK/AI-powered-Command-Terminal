import os
import uuid
import pickle  # <-- Import pickle for saving/loading the registry
from dotenv import load_dotenv

# LangChain and LangGraph imports
from langchain_groq import ChatGroq
from langchain_milvus import Milvus
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langgraph.store.base import BaseStore

# BigTool imports
from langgraph_bigtool import create_agent

# Local imports
from .dynamic_tools import load_system_command_tools
from pymilvus import MilvusClient

# --- Configuration ---
MILVUS_COLLECTION_NAME = "system_command_tools_runtime"
MILVUS_CONNECTION_ARGS = {"host": "localhost", "port": "19530"}
MILVUS_URI = f"http://{MILVUS_CONNECTION_ARGS['host']}:{MILVUS_CONNECTION_ARGS['port']}"
# --- NEW: Define a path for the cached tool registry ---
TOOL_REGISTRY_CACHE_PATH = ".tool_registry.pkl"
# ---

class SearchResult:
    """A simple class to wrap search results with the expected interface"""
    def __init__(self, key, score):
        self.key = key
        self.score = score
    
    def __repr__(self):
        return f"SearchResult(key='{self.key}', score={self.score})"

class MilvusStoreWrapper(BaseStore):
    def __init__(self, vector_store: Milvus, tool_registry: dict):
        self.vector_store = vector_store
        self.tool_registry = tool_registry  # Store reference to tool registry
    
    def search(self, *args, **kwargs):
        """Flexible search method that handles different call signatures"""
        # Debug: Print what we're receiving
        print(f"Debug: search called with args={args}, kwargs={kwargs}")
        
        # Handle different ways the search method might be called
        query = None
        k = 5  # default
        
        if args:
            # Extract query from first argument, handling different data types
            first_arg = args[0]
            if isinstance(first_arg, str):
                query = first_arg
            elif isinstance(first_arg, (tuple, list)) and len(first_arg) > 0:
                query = str(first_arg[0])  # Convert to string
            elif hasattr(first_arg, 'query'):  # If it's an object with query attribute
                query = str(first_arg.query)
            else:
                query = str(first_arg)  # Try to convert whatever it is to string
            
            # Get k from second argument if present
            if len(args) > 1:
                k = args[1] if isinstance(args[1], int) else 5
        
        # Also check kwargs
        if 'query' in kwargs:
            query = str(kwargs['query'])
        if 'k' in kwargs:
            k = kwargs['k'] if isinstance(kwargs['k'], int) else 5
        elif 'limit' in kwargs:  # LangGraph might use 'limit' instead of 'k'
            # Increase the limit to get more relevant results
            k = max(kwargs['limit'] * 3, 10) if isinstance(kwargs['limit'], int) else 10
        
        # Ensure we have a valid query string
        if not query or not isinstance(query, str):
            print(f"Warning: Invalid query: {query}")
            return []
        
        print(f"Debug: Searching with query='{query}', k={k}")
        
        try:
            results = self.vector_store.similarity_search_with_score(query, k=k)
            # Return SearchResult objects instead of tuples
            search_results = [SearchResult(key=doc.metadata["tool_id"], score=score) 
                            for doc, score in results]
            print(f"Debug: Found {len(search_results)} results")
            # Print what tools were found
            if search_results:
                print("Debug: Search results:")
                for i, result in enumerate(search_results):
                    # Get the actual tool name from registry
                    tool = self.tool_registry.get(result.key)
                    tool_name = tool.name if tool else "Unknown"
                    print(f"  {i+1}. {tool_name} (ID: {result.key[:8]}..., score: {result.score:.3f})")
            return search_results
        except Exception as e:
            print(f"Warning: Search failed: {e}")
            print(f"Debug: Query type: {type(query)}, Query value: {repr(query)}")
            return []
    
    def get(self, key, **kwargs):
        """Get method for BaseStore compatibility - THIS IS CRUCIAL"""
        print(f"Debug: get() called for key: {key}")
        tool = self.tool_registry.get(key)
        if tool:
            print(f"Debug: Retrieved tool: {tool.name}")
        else:
            print(f"Debug: Tool not found for key: {key}")
        return tool
    
    def put(self, key, value, **kwargs):
        """Put method for BaseStore compatibility"""
        self.tool_registry[key] = value
    
    def delete(self, key, **kwargs):
        """Delete method for BaseStore compatibility"""
        if key in self.tool_registry:
            del self.tool_registry[key]
    
    def batch(self, operations):
        """Synchronous batch operation - required by BaseStore interface"""
        results = []
        for op in operations:
            # Handle different operation types as needed
            if hasattr(op, 'operation') and op.operation == 'search':
                result = self.search(op.query, op.k)
                results.append(result)
            elif hasattr(op, 'operation') and op.operation == 'get':
                result = self.get(op.key)
                results.append(result)
            else:
                # For unsupported operations, return empty result
                results.append([])
        return results
    
    async def abatch(self, operations):
        """Asynchronous batch operation - required by BaseStore interface"""
        # For simplicity, we'll just call the synchronous version
        # In a production environment, you might want to implement true async operations
        return self.batch(operations)

def collection_exists(name: str) -> bool:
    """Checks if a Milvus collection exists using the MilvusClient."""
    try:
        client = MilvusClient(uri=MILVUS_URI)
        return client.has_collection(collection_name=name)
    except Exception as e:
        print(f"Warning: Could not connect to Milvus to check for collection: {e}")
        return False

def load_tool_registry_from_cache():
    """
    Attempts to load the tool registry from cache with proper error handling.
    Returns the registry if successful, None if it fails.
    """
    if not os.path.exists(TOOL_REGISTRY_CACHE_PATH):
        return None
    
    try:
        # Check if the file is empty
        if os.path.getsize(TOOL_REGISTRY_CACHE_PATH) == 0:
            print("⚠️  Tool registry cache file is empty. Will rebuild from scratch.")
            os.remove(TOOL_REGISTRY_CACHE_PATH)
            return None
        
        with open(TOOL_REGISTRY_CACHE_PATH, "rb") as f:
            tool_registry = pickle.load(f)
        
        # Validate the loaded registry
        if not isinstance(tool_registry, dict):
            raise ValueError("Tool registry cache contains invalid data structure")
        
        if len(tool_registry) == 0:
            raise ValueError("Tool registry cache is empty")
        
        # Quick validation that the tools have the expected structure
        for tool_id, tool in tool_registry.items():
            if not hasattr(tool, 'name') or not hasattr(tool, 'description'):
                raise ValueError(f"Invalid tool structure for tool_id: {tool_id}")
        
        print(f"✅ Successfully loaded {len(tool_registry)} tools from cache.")
        return tool_registry
        
    except (pickle.PickleError, EOFError, ValueError) as e:
        print(f"⚠️  Tool registry cache is corrupted ({e}). Will rebuild from scratch.")
        # Remove the corrupted cache file
        try:
            os.remove(TOOL_REGISTRY_CACHE_PATH)
        except OSError:
            pass
        return None
    except Exception as e:
        print(f"⚠️  Unexpected error loading tool registry cache ({e}). Will rebuild from scratch.")
        return None

def save_tool_registry_to_cache(tool_registry):
    """
    Saves the tool registry to cache with proper error handling.
    """
    try:
        # Create a backup of existing cache if it exists
        if os.path.exists(TOOL_REGISTRY_CACHE_PATH):
            backup_path = f"{TOOL_REGISTRY_CACHE_PATH}.backup"
            try:
                os.rename(TOOL_REGISTRY_CACHE_PATH, backup_path)
            except OSError:
                pass
        
        # Write the new cache
        with open(TOOL_REGISTRY_CACHE_PATH, "wb") as f:
            pickle.dump(tool_registry, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        # Remove backup if save was successful
        backup_path = f"{TOOL_REGISTRY_CACHE_PATH}.backup"
        if os.path.exists(backup_path):
            try:
                os.remove(backup_path)
            except OSError:
                pass
        
        print(f"✅ Tool registry saved to '{TOOL_REGISTRY_CACHE_PATH}' for future runs.")
        return True
        
    except Exception as e:
        print(f"⚠️  Failed to save tool registry to cache: {e}")
        # Restore backup if it exists
        backup_path = f"{TOOL_REGISTRY_CACHE_PATH}.backup"
        if os.path.exists(backup_path):
            try:
                os.rename(backup_path, TOOL_REGISTRY_CACHE_PATH)
                print("✅ Restored previous cache from backup.")
            except OSError:
                pass
        return False

def create_bigtool_agent():
    """
    Creates and returns a LangGraph agent.
    It builds the tool index and registry only if they don't already exist.
    """
    load_dotenv()
    print("--- Initializing Agent ---")

    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    # --- ENHANCED LOGIC WITH BETTER ERROR HANDLING ---
    # Check if the collection AND the cached registry exist and can be loaded.
    tool_registry = None
    if collection_exists(MILVUS_COLLECTION_NAME):
        print(f"✅ Found existing Milvus collection.")
        tool_registry = load_tool_registry_from_cache()
        
        if tool_registry is not None:
            print("   Skipping tool discovery for a fast startup.")
        else:
            print("   But tool registry cache is missing or corrupted.")

    if tool_registry is None:
        print(f"Building tool registry from scratch...")
        
        # 1. Load tools from PATH (the slow part)
        all_tools = load_system_command_tools()

        # 2. Create the tool_registry
        tool_registry = {str(uuid.uuid4()): tool for tool in all_tools}
        print(f"✅ Created Tool Registry with {len(tool_registry)} tools.")

        # 3. Save the new registry to the cache file for next time
        save_tool_registry_to_cache(tool_registry)

        # 4. Create and populate the Milvus store
        print("Creating and populating Milvus index...")
        documents_to_index = [
            Document(
                page_content=f"{tool.name}: {tool.description}",
                metadata={"tool_id": tool_id},
            )
            for tool_id, tool in tool_registry.items()
        ]
        
        try:
            Milvus.from_documents(
                documents_to_index,
                embedding=embeddings,
                collection_name=MILVUS_COLLECTION_NAME,
                connection_args=MILVUS_CONNECTION_ARGS,
                drop_old=True
            )
            print("✅ Milvus index populated successfully.")
        except Exception as e:
            print(f"❌ Could not connect to or populate Milvus: {e}")
            raise

    # --- The rest of the logic is now common for both paths ---
    try:
        vector_store = Milvus(
            embedding_function=embeddings,
            collection_name=MILVUS_COLLECTION_NAME,
            connection_args=MILVUS_CONNECTION_ARGS,
        )
    except Exception as e:
        print(f"❌ Failed to connect to Milvus vector store: {e}")
        raise
    
    try:
        llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)  # Use a more reliable model
        builder = create_agent(llm, tool_registry)
        milvus_as_langgraph_store = MilvusStoreWrapper(vector_store=vector_store, tool_registry=tool_registry)  # Pass the registry
        agent = builder.compile(store=milvus_as_langgraph_store)
    except Exception as e:
        print(f"❌ Failed to create agent: {e}")
        raise

    print("--- Agent Initialized and Ready ---")
    return agent