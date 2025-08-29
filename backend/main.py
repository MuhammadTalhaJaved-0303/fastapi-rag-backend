
import os
import shutil
import time
import asyncio
from collections import deque
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from services import (
    process_and_store_pdf, get_retriever_for_user, save_chat_history,
    get_user_db, save_user_db, DOCUMENTS_PATH, CHROMA_DB_PATH,
    remove_user_data, remove_file_data, get_retriever_for_conversation
)

# Ollama/local load-balancing removed. We now select provider based on available API keys.

# --- Initial Setup ---
limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

security = HTTPBasic()

# --- Authentication ---
def authenticate_user(credentials: HTTPBasicCredentials = Depends(security)):
    users_db = get_user_db()
    user = users_db.get(credentials.username)
    if not user or user["password"] != credentials.password:
        raise HTTPException(status_code=401, detail="Incorrect username or password", headers={"WWW-Authenticate": "Basic"})
    return credentials.username

    # --- Helper function to format the prompt for logging ---
def format_prompt_for_logging(query, source_documents):
    
    # Separate documents and chat history
    docs = [doc for doc in source_documents if doc.metadata.get("source") != "chat_history"]
    history = [doc for doc in source_documents if doc.metadata.get("source") == "chat_history"]

    prompt = "    Previous conversation:\n"
    for conv in history:
        prompt += f"    {conv.page_content.replace('Question: ', '').split('Answer:')[0].strip()}"

    prompt += "\n\n    Relevant documents:\n"
    for doc in docs:
        prompt += f"    {doc.page_content}\n"

    prompt += f"\n    User: {query}"
    prompt += "\n    Answer:"
    return prompt

# --- API Endpoints ---
@app.post("/query/")
@limiter.limit("1500/minute")
async def query_agent(
    request: Request,
    user_id: str = Depends(authenticate_user),
    query: str = Form(...),
    conversation_id: str = Form(None)
):
    if conversation_id:
        retriever = get_retriever_for_conversation(user_id, conversation_id)
    else:
        retriever = get_retriever_for_user(user_id)
        
    if not retriever:
        raise HTTPException(status_code=404, detail="No documents found for this user. Please upload files first.")

    # Provider selection: prefer OpenAI (gpt-4o-mini), otherwise Gemini (gemini-2.0-flash)
    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    llm = None
    if openai_key:
        print("Using OpenAI (gpt-4o-mini)")
        llm = ChatOpenAI(model_name=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0.7)
    elif gemini_key:
        print("Using Gemini (gemini-2.0-flash)")
        llm = ChatGoogleGenerativeAI(model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"), temperature=0.7, google_api_key=gemini_key)
    else:
        raise HTTPException(status_code=500, detail=(
            "No API keys configured. Set OPENAI_API_KEY for OpenAI (gpt-4o-mini) "
            "or GEMINI_API_KEY/GOOGLE_API_KEY for Gemini (gemini-2.0-flash)."
        ))

    # Stricter prompt to prevent hallucinations and force citation-based answers
    qa_prompt = PromptTemplate(
        input_variables=["context", "question"],
        template=(
            "You are a helpful assistant. Answer the question using ONLY the information in the context.\n"
            "If the answer is not in the context, say 'I don't know from the provided documents.'\n"
            "Be concise.\n\n"
            "Context:\n{context}\n\nQuestion: {question}\nAnswer:"
        ),
    )

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": qa_prompt},
    )

    try:
        result = qa_chain.invoke({"query": query})
    except Exception as e:
        print(f"Primary LLM call failed, trying fallback: {e}")
        # Fallback to the other provider if available
        if openai_key and gemini_key:
            try:
                print("Falling back to Gemini (gemini-2.0-flash)")
                llm = ChatGoogleGenerativeAI(model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"), temperature=0.7, google_api_key=gemini_key)
                qa_chain = RetrievalQA.from_chain_type(
                    llm=llm,
                    chain_type="stuff",
                    retriever=retriever,
                    return_source_documents=True,
                    chain_type_kwargs={"prompt": qa_prompt},
                )
                result = qa_chain.invoke({"query": query})
            except Exception as fallback_error:
                print(f"Fallback to Gemini failed: {fallback_error}")
                raise HTTPException(status_code=503, detail="All AI services are currently unavailable")
        elif gemini_key and not openai_key:
            # Already tried Gemini; no other fallback
            raise HTTPException(status_code=503, detail="Gemini service is currently unavailable")
        elif openai_key and not gemini_key:
            # Already tried OpenAI; no other fallback
            raise HTTPException(status_code=503, detail="OpenAI service is currently unavailable")
    answer = result["result"]
    
    # Save the interaction to chat history
    save_chat_history(user_id, query, answer, conversation_id)
    
    # Format the prompt for logging
    formatted_prompt = format_prompt_for_logging(query, result["source_documents"])

    return {
        "response": answer, 
        "prompt": formatted_prompt,
        "source_documents": [
            {
                "page_content": doc.page_content,
                "metadata": doc.metadata,
            } for doc in result["source_documents"]
        ]
    }

# --- Admin Endpoints ---
@app.post("/admin/users/add")
def add_user(user_id: str = Form(...), password: str = Form(...), admin_user: str = Depends(authenticate_user)):
    # In a real app, you'd have proper admin roles. Here, any authenticated user can add another.
    users_db = get_user_db()
    if user_id in users_db:
        raise HTTPException(status_code=400, detail="User already exists.")
    users_db[user_id] = {"password": password, "files": []}
    save_user_db(users_db)
    return {"message": f"User '{user_id}' added successfully."}

@app.post("/admin/users/remove")
def remove_user(user_id_to_remove: str = Form(...), admin_user: str = Depends(authenticate_user)):
    success, message = remove_user_data(user_id_to_remove)
    if not success:
        raise HTTPException(status_code=404, detail=message)
    return {"message": message}

@app.post("/admin/files/remove")
def remove_file(
    file_name: str = Form(...),
    user_id_for_file: str = Form(None), # The user to associate the file with. None for shared.
    admin_user: str = Depends(authenticate_user)
):
    success, message = remove_file_data(file_name, user_id_for_file)
    if not success:
        raise HTTPException(status_code=404, detail=message)
    return {"message": message}

@app.post("/admin/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    user_id_for_file: str = Form(None), # The user to associate the file with. None for shared.
    admin_user: str = Depends(authenticate_user)
):
    is_shared = not user_id_for_file

    
    if is_shared:
        collection_name = "docs_shared"
        save_path_dir = os.path.join(DOCUMENTS_PATH, "shared")
    else:
        collection_name = f"docs_user_{user_id_for_file}"
        save_path_dir = os.path.join(DOCUMENTS_PATH, "users", user_id_for_file)
    
    os.makedirs(save_path_dir, exist_ok=True)
    file_path = os.path.join(save_path_dir, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    process_and_store_pdf(file_path, collection_name)

    # Update user DB with file info
    users_db = get_user_db()
    if not is_shared and user_id_for_file in users_db:
        users_db[user_id_for_file]["files"].append(file.filename)
        save_user_db(users_db)

    return {"message": f"File '{file.filename}' uploaded to collection '{collection_name}'."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
