
import os
import shutil
import stat
import time
import json
from typing import Optional
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma
from langchain.retrievers import MergerRetriever
from langchain.schema import Document

from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from chromadb.errors import InvalidArgumentError

# --- Paths and Configuration ---
load_dotenv()
# Check if running in AWS and use the EFS mount path, otherwise use local path
EFS_MOUNT_PATH = "/mnt/efs"
EFS_PATH = EFS_MOUNT_PATH if os.path.exists(EFS_MOUNT_PATH) else os.path.join(os.path.dirname(os.path.dirname(__file__)), "efs")

CHROMA_DB_PATH = os.path.join(EFS_PATH, "chroma_db")
DOCUMENTS_PATH = os.path.join(EFS_PATH, "documents")
USER_DB_PATH = os.path.join(EFS_PATH, "user_db.json")

# --- Initial Setup ---
os.makedirs(CHROMA_DB_PATH, exist_ok=True)
os.makedirs(os.path.join(DOCUMENTS_PATH, "users"), exist_ok=True)
os.makedirs(os.path.join(DOCUMENTS_PATH, "shared"), exist_ok=True)

# --- Filesystem utilities (Windows-safe removals) ---
def _on_remove_error(func, path, exc_info):
    """Retry removal by fixing permissions when encountering PermissionError."""
    try:
        os.chmod(path, stat.S_IWRITE)
    except Exception:
        pass
    try:
        func(path)
    except Exception:
        raise


def safe_rmtree(target_path: str, max_retries: int = 3, retry_delay_seconds: float = 0.2) -> bool:
    """Remove a directory tree robustly across platforms.

    Returns True if removed or not present; False if still exists after retries.
    """
    if not os.path.exists(target_path):
        return True
    for attempt_index in range(max_retries):
        try:
            shutil.rmtree(target_path, onerror=_on_remove_error)
            return True
        except Exception:
            time.sleep(retry_delay_seconds * (attempt_index + 1))
    return not os.path.exists(target_path)

# --- Embedding Model Selection with robust fallback ---
def _choose_embeddings():
    # Prefer OpenAI
    if os.getenv("OPENAI_API_KEY"):
        try:
            print("Using OpenAI 'text-embedding-3-small' for embeddings.")
            return OpenAIEmbeddings(model="text-embedding-3-small")
        except Exception as e:
            print(f"Failed to initialize OpenAI embeddings: {e}")

    # Then Gemini (free tier)
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        try:
            configured_model = os.getenv("GEMINI_EMBEDDING_MODEL", "models/text-embedding-004")
            # Ensure correct resource format for Google client
            if not configured_model.startswith("models/"):
                configured_model = f"models/{configured_model}"
            print(f"Using Gemini embeddings model: {configured_model}")
            return GoogleGenerativeAIEmbeddings(model=configured_model, google_api_key=gemini_key)
        except Exception as e:
            print(f"Failed to initialize Gemini embeddings: {e}")

    # No local fallback to keep the build small and torch-free
    raise RuntimeError(
        "No embedding provider configured. Set OPENAI_API_KEY (uses text-embedding-3-small) "
        "or GEMINI_API_KEY/GOOGLE_API_KEY (uses text-embedding-004)."
    )

embeddings = _choose_embeddings()

# --- User Management (simple JSON-based) ---
def get_user_db():
    if not os.path.exists(USER_DB_PATH):
        # Create a default admin user if the db doesn't exist
        print("User database not found. Creating one with a default admin user.")
        default_db = {
            "admin": {
                "password": "admin",
                "files": []
            }
        }
        save_user_db(default_db)
        return default_db
    with open(USER_DB_PATH, 'r') as f:
        return json.load(f)

def save_user_db(db):
    with open(USER_DB_PATH, 'w') as f:
        json.dump(db, f, indent=4)

def remove_user_data(user_id: str):
    """Removes all data associated with a user."""
    users_db = get_user_db()
    if user_id not in users_db:
        return False, "User not found."

    # 1. Remove from user_db.json
    del users_db[user_id]
    save_user_db(users_db)

    # 2. Remove user's private documents directory
    user_docs_dir = os.path.join(DOCUMENTS_PATH, "users", user_id)
    if os.path.exists(user_docs_dir):
        safe_rmtree(user_docs_dir)

    # 3. Remove user's private ChromaDB collection
    user_chroma_collection = os.path.join(CHROMA_DB_PATH, f"docs_user_{user_id}")
    if os.path.exists(user_chroma_collection):
        safe_rmtree(user_chroma_collection)

    # 4. Remove user's chat history ChromaDB collection
    history_chroma_collection = os.path.join(CHROMA_DB_PATH, f"history_{user_id}")
    if os.path.exists(history_chroma_collection):
        safe_rmtree(history_chroma_collection)

    return True, f"User '{user_id}' and all their data removed successfully."

def remove_file_data(file_name: str, user_id_for_file: str = None):
    """Removes a file and its associated data."""
    is_shared = user_id_for_file is None
    
    if is_shared:
        file_path = os.path.join(DOCUMENTS_PATH, "shared", file_name)
        collection_name = "docs_shared"
    else:
        file_path = os.path.join(DOCUMENTS_PATH, "users", user_id_for_file, file_name)
        collection_name = f"docs_user_{user_id_for_file}"

    if not os.path.exists(file_path):
        return False, f"File '{file_name}' not found."

    # 1. Delete the file
    os.remove(file_path)

    # 2. Remove the file from the user's file list in user_db.json
    if not is_shared:
        users_db = get_user_db()
        if user_id_for_file in users_db and file_name in users_db[user_id_for_file]["files"]:
            users_db[user_id_for_file]["files"].remove(file_name)
            save_user_db(users_db)

    # 3. Rebuild the ChromaDB collection without the deleted file
    rebuild_collection(collection_name)

    return True, f"File '{file_name}' removed successfully."

def rebuild_collection(collection_name: str):
    """Rebuilds a ChromaDB collection from the documents in its corresponding folder."""
    persist_dir = os.path.join(CHROMA_DB_PATH, collection_name)
    if os.path.exists(persist_dir):
        safe_rmtree(persist_dir)

    if "user" in collection_name:
        user_id = collection_name.split('_')[-1]
        docs_path = os.path.join(DOCUMENTS_PATH, "users", user_id)
    else:
        docs_path = os.path.join(DOCUMENTS_PATH, "shared")

    if not os.path.exists(docs_path):
        return

    all_splits = []
    for filename in os.listdir(docs_path):
        if filename.lower().endswith(".pdf"):
            file_path = os.path.join(docs_path, filename)
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            splits = text_splitter.split_documents(documents)
            all_splits.extend(splits)

    if all_splits:
        vectorstore = Chroma.from_documents(documents=all_splits, embedding=embeddings, persist_directory=persist_dir)
        vectorstore.persist()


# --- PDF and Vector Store Functions ---
def process_and_store_pdf(file_path: str, collection_name: str):
    """Loads a PDF, splits it, and stores it in a Chroma collection.

    If an embedding dimension mismatch is detected (e.g., switching from local
    embeddings to OpenAI or vice versa), automatically rebuild the collection with
    the current embedding model and retry the insertion.
    """
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(documents)
    
    persist_dir = os.path.join(CHROMA_DB_PATH, collection_name)
    try:
        vectorstore = Chroma.from_documents(
            documents=splits,
            embedding=embeddings,
            persist_directory=persist_dir,
        )
    except InvalidArgumentError as e:
        # Handle embedding dimension mismatch by rebuilding the collection
        if "dimension" in str(e) or "embedding" in str(e):
            safe_rmtree(persist_dir)
            vectorstore = Chroma.from_documents(
                documents=splits,
                embedding=embeddings,
                persist_directory=persist_dir,
            )
        else:
            raise
    return True

def save_chat_history(user_id: str, question: str, answer: str, conversation_id: str = None):
    """Saves a Q&A pair to the user's chat history collection."""
    if conversation_id:
        collection_name = f"history_{user_id}_{conversation_id}"
    else:
        collection_name = f"history_{user_id}"
        
    persist_dir = os.path.join(CHROMA_DB_PATH, collection_name)
    
    # Create a document from the Q&A pair
    doc_text = f"Question: {question}\nAnswer: {answer}"
    doc = Document(
        page_content=doc_text,
        metadata={"source": "chat_history"}
    )
    
    vectorstore = Chroma(persist_directory=persist_dir, embedding_function=embeddings)
    vectorstore.add_documents([doc])

# --- Retriever Functions ---
from typing import Optional


def _build_search_kwargs(k: int, doc_filter: Optional[str] = None):
    if doc_filter:
        # Filter by metadata 'source' containing the substring (file path)
        return {"k": k, "filter": {"source": {"$contains": doc_filter}}}
    return {"k": k}


def get_retriever_for_user(user_id: str, doc_filter: Optional[str] = None):
    """Gets a combined retriever for a user's private docs, shared docs, and chat history.

    Chat history is included with a small k to provide context while minimizing contamination.
    Optional doc_filter (substring match) restricts private/shared by metadata 'source' (not applied to history).
    """
    retrievers = []

    # 1. User's private documents
    user_collection = f"docs_user_{user_id}"
    user_db_path = os.path.join(CHROMA_DB_PATH, user_collection)
    if os.path.exists(user_db_path):
        user_vectorstore = Chroma(persist_directory=user_db_path, embedding_function=embeddings)
        retrievers.append(
            user_vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs=_build_search_kwargs(3, doc_filter),
            )
        )

    # 2. Shared documents
    shared_collection = "docs_shared"
    shared_db_path = os.path.join(CHROMA_DB_PATH, shared_collection)
    if os.path.exists(shared_db_path):
        shared_vectorstore = Chroma(persist_directory=shared_db_path, embedding_function=embeddings)
        retrievers.append(
            shared_vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs=_build_search_kwargs(3, doc_filter),
            )
        )

    # 3. User's chat history (small k)
    history_collection = f"history_{user_id}"
    history_db_path = os.path.join(CHROMA_DB_PATH, history_collection)
    if os.path.exists(history_db_path):
        history_vectorstore = Chroma(persist_directory=history_db_path, embedding_function=embeddings)
        retrievers.append(
            history_vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 2},
            )
        )

    if not retrievers:
        return None

    # Create a unified retriever
    return MergerRetriever(retrievers=retrievers)

def get_retriever_for_conversation(user_id: str, conversation_id: str, doc_filter: Optional[str] = None):
    """Gets a combined retriever for a user's docs, shared docs, and conversation history.

    Conversation history is included with a small k. Optional doc_filter restricts private/shared only.
    """
    retrievers = []

    # 1. User's private documents
    user_collection = f"docs_user_{user_id}"
    user_db_path = os.path.join(CHROMA_DB_PATH, user_collection)
    if os.path.exists(user_db_path):
        user_vectorstore = Chroma(persist_directory=user_db_path, embedding_function=embeddings)
        retrievers.append(
            user_vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs=_build_search_kwargs(3, doc_filter),
            )
        )

    # 2. Shared documents
    shared_collection = "docs_shared"
    shared_db_path = os.path.join(CHROMA_DB_PATH, shared_collection)
    if os.path.exists(shared_db_path):
        shared_vectorstore = Chroma(persist_directory=shared_db_path, embedding_function=embeddings)
        retrievers.append(
            shared_vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs=_build_search_kwargs(3, doc_filter),
            )
        )

    # 3. Conversation-specific chat history (small k)
    conversation_history_collection = f"history_{user_id}_{conversation_id}"
    conversation_history_db_path = os.path.join(CHROMA_DB_PATH, conversation_history_collection)
    if os.path.exists(conversation_history_db_path):
        conversation_history_vectorstore = Chroma(persist_directory=conversation_history_db_path, embedding_function=embeddings)
        retrievers.append(
            conversation_history_vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 2},
            )
        )

    if not retrievers:
        return None

    return MergerRetriever(retrievers=retrievers)
