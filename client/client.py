
import requests
import os
import threading
import time
import random
import argparse
from datetime import datetime
import json

# --- Configuration ---
BASE_URL = "http://127.0.0.1:8000"
LOG_FILE = "log.jsonl"

# --- API Communication Functions ---

def handle_api_error(e: requests.exceptions.RequestException):
    """Provides more detailed error messages from API responses."""
    if e.response is not None:
        try:
            error_details = e.response.json()
            return {"error": f"API Error: {e.response.status_code} {e.response.reason}", "details": error_details.get("detail", "No details provided.")}
        except json.JSONDecodeError:
            return {"error": f"API Error: {e.response.status_code} {e.response.reason}", "details": e.response.text}
    return {"error": str(e)}

def add_user(admin_user, admin_pass, new_user, new_pass):
    url = f"{BASE_URL}/admin/users/add"
    try:
        response = requests.post(url, auth=(admin_user, admin_pass), data={"user_id": new_user, "password": new_pass})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return handle_api_error(e)

def remove_user(admin_user, admin_pass, user_to_remove):
    url = f"{BASE_URL}/admin/users/remove"
    try:
        response = requests.post(url, auth=(admin_user, admin_pass), data={"user_id_to_remove": user_to_remove})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return handle_api_error(e)

def upload_file(user, password, file_path, user_for_file=None):
    url = f"{BASE_URL}/admin/files/upload"
    try:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "application/pdf")}
            data = {"user_id_for_file": user_for_file} # Send None for shared
            response = requests.post(url, auth=(user, password), files=files, data=data)
            response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return handle_api_error(e)

def upload_directory(user, password, dir_path, user_for_file=None):
    results = []
    if not os.path.isdir(dir_path):
        return {"error": f"Directory not found at {dir_path}"}
    
    for filename in os.listdir(dir_path):
        if filename.lower().endswith(".pdf"):
            file_path = os.path.join(dir_path, filename)
            print(f"Uploading {file_path}...")
            result = upload_file(user, password, file_path, user_for_file)
            results.append({filename: result})
    return results

def remove_file(user, password, file_name, for_user=None):
    url = f"{BASE_URL}/admin/files/remove"
    try:
        data = {"file_name": file_name, "user_id_for_file": for_user}

        response = requests.post(url, auth=(user, password), data=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return handle_api_error(e)

def query_agent(user, password, query, conversation_id=None):
    url = f"{BASE_URL}/query/"
    try:
        data = {"query": query}
        if conversation_id:
            data["conversation_id"] = conversation_id
        response = requests.post(url, auth=(user, password), data=data, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return handle_api_error(e)

def format_log_entry(user_id, question, response):
    """Formats a log entry based on the new, more detailed format."""
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    log_entry = "******************************\n"
    log_entry += f"Time: {timestamp}\n"
    log_entry += f"User: {user_id}\n"
    log_entry += f"Message: {question}\n"
    log_entry += f"Response: {response.get('response', 'ERROR')}\n"
    log_entry += f"Prompt: \n{response.get('prompt', 'PROMPT_NOT_RETURNED_BY_SERVER')}\n"
    
    # Add source documents for context
    source_docs = response.get('source_documents', [])
    if source_docs:
        log_entry += "\n--- Source Documents ---\n"
        for doc in source_docs:
            metadata = doc.get('metadata', {})
            log_entry += f"  Source: {metadata.get('source')}, Page: {metadata.get('page')}\n"
            log_entry += f"  Content: {doc.get('page_content', '').strip()}\n\n"

    log_entry += "******************************"
    return log_entry

# --- Load Testing Functions ---

def load_test_worker(user_id, password, questions, log_lock, stats):
    while not stats["stop"]:
        question = random.choice(questions)
        
        start_time = time.time()
        response = query_agent(user_id, password, question)
        end_time = time.time()

        with log_lock:
            stats["total_requests"] += 1
            stats["total_time"] += (end_time - start_time)
            
            log_entry = {
                "timestamp_start": datetime.fromtimestamp(start_time).isoformat(),
                "timestamp_end": datetime.fromtimestamp(end_time).isoformat(),
                "duration": round(end_time - start_time, 4),
                "user_id": user_id,
                "question": question,
                "answer": response.get('response', 'ERROR'),
                "prompt": response.get('prompt', 'PROMPT_NOT_RETURNED_BY_SERVER') 
            }

            with open(LOG_FILE, "a") as f:
                f.write(json.dumps(log_entry) + "\n")

        time.sleep(random.uniform(0.5, 1.5))

def run_load_test(num_threads, questions_file, admin_user, admin_pass):
    print(f"Starting load test with {num_threads} threads...")
    print("Preparing users for the test...")

    # Create users for the test
    for i in range(num_threads):
        user_id = f"loadtest_user_{i}"
        password = "password"
        add_user(admin_user, admin_pass, user_id, password)
    print(f"{num_threads} users created.")

    try:
        with open(questions_file, 'r') as f:
            questions = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: Questions file not found at {questions_file}")
        return

    log_lock = threading.Lock()
    threads = []
    stats = {"total_requests": 0, "total_time": 0.0, "stop": False}

    for i in range(num_threads):
        user_id = f"loadtest_user_{i}"
        password = "password"
        thread = threading.Thread(target=load_test_worker, args=(user_id, password, questions, log_lock, stats))
        threads.append(thread)
        thread.start()

    start_time = time.time()
    try:
        while True:
            time.sleep(10)
            elapsed_time = time.time() - start_time
            with log_lock:
                if stats["total_requests"] > 0:
                    avg_time = stats["total_time"] / stats["total_requests"]
                    rpm = (stats["total_requests"] / elapsed_time) * 60
                    print(f"[{datetime.now().strftime('%H:%M:%M')}] Requests: {stats['total_requests']}, RPM: {rpm:.2f}, Avg Response Time: {avg_time:.4f}s")
    except KeyboardInterrupt:
        print("\nStopping load test...")
        stats["stop"] = True
    
    for thread in threads:
        thread.join()
    print("Load test finished.")

# --- Main Execution & CLI Parsing ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Client for RAG Agent API.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Credentials for admin actions
    admin_parser = argparse.ArgumentParser(add_help=False)
    admin_parser.add_argument("--admin-user", required=True, help="Admin user ID.")
    admin_parser.add_argument("--admin-pass", required=True, help="Admin password.")

    # 'user-add' command
    parser_add = subparsers.add_parser("user-add", parents=[admin_parser], help="Add a new user.")
    parser_add.add_argument("--new-user", required=True, help="ID for the new user.")
    parser_add.add_argument("--new-pass", required=True, help="Password for the new user.")

    # 'user-remove' command
    parser_remove = subparsers.add_parser("user-remove", parents=[admin_parser], help="Remove a user.")
    parser_remove.add_argument("--user-to-remove", required=True, help="ID of the user to remove.")

    # 'upload' command
    parser_upload = subparsers.add_parser("upload", help="Upload a PDF file.")
    parser_upload.add_argument("--user", required=True, help="User ID for authentication.")
    parser_upload.add_argument("--password", required=True, help="Password for authentication.")
    parser_upload.add_argument("--file", required=True, help="Path to the PDF file.")
    parser_upload.add_argument("--for-user", help="User ID to associate the file with. Omit for shared.")

    # 'file-remove' command
    parser_file_remove = subparsers.add_parser("file-remove", help="Remove a file.")
    parser_file_remove.add_argument("--user", required=True, help="User ID for authentication.")
    parser_file_remove.add_argument("--password", required=True, help="Password for authentication.")
    parser_file_remove.add_argument("--file-name", required=True, help="Name of the file to remove.")
    parser_file_remove.add_argument("--for-user", help="User ID the file is associated with. Omit for shared.")

    # 'upload-dir' command
    parser_upload_dir = subparsers.add_parser("upload-dir", help="Upload all PDFs from a directory.")
    parser_upload_dir.add_argument("--user", required=True, help="User ID for authentication.")
    parser_upload_dir.add_argument("--password", required=True, help="Password for authentication.")
    parser_upload_dir.add_argument("--dir", required=True, help="Path to the directory with PDF files.")
    parser_upload_dir.add_argument("--for-user", help="User ID to associate the files with. Omit for shared.")

    # 'query' command
    parser_query = subparsers.add_parser("query", help="Query the RAG agent.")
    parser_query.add_argument("--user", required=True, help="User ID for authentication.")
    parser_query.add_argument("--password", required=True, help="Password for the user.")
    parser_query.add_argument("--query", required=True, help="The query text to send to the agent.")
    parser_query.add_argument("--conversation-id", help="An ID to maintain conversation history.")

    # 'load-test' command
    parser_load_test = subparsers.add_parser("load-test", parents=[admin_parser], help="Run a load test.")
    parser_load_test.add_argument("--threads", type=int, default=30, help="Number of concurrent threads.")
    parser_load_test.add_argument("--questions", default="test_data/questions.txt", help="Path to questions file.")

    args = parser.parse_args()

    if args.command == "user-add":
        print(add_user(args.admin_user, args.admin_pass, args.new_user, args.new_pass))
    elif args.command == "user-remove":
        print(remove_user(args.admin_user, args.admin_pass, args.user_to_remove))
    elif args.command == "upload":
        print(upload_file(args.user, args.password, args.file, args.for_user))
    elif args.command == "file-remove":
        print(json.dumps(remove_file(args.user, args.password, args.file_name, args.for_user), indent=4))
    elif args.command == "upload-dir":
        print(upload_directory(args.user, args.password, args.dir, args.for_user))
    elif args.command == "query":
        response = query_agent(args.user, args.password, args.query, args.conversation_id)
        log_output = format_log_entry(args.user, args.query, response)
        print(log_output)
        with open("query_log.txt", "a", encoding="utf-8") as f:
            f.write(log_output + "\n")
    elif args.command == "load-test":
        run_load_test(args.threads, args.questions, args.admin_user, args.admin_pass)
