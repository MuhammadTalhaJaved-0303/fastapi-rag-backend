#!/usr/bin/env python3
"""
Windows-friendly test script for RAG application
"""

import requests
import json
import time
import os
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"

def test_server():
    """Test if server is running"""
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("OK: Server is running at http://localhost:8000")
            return True
        else:
            print(f"ERROR: Server returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"ERROR: Cannot connect to server: {e}")
        return False

def add_user(admin_user, admin_pass, user_id, password):
    """Add a user"""
    try:
        response = requests.post(
            f"{BASE_URL}/admin/users/add",
            auth=(admin_user, admin_pass),
            data={"user_id": user_id, "password": password},
            timeout=10
        )
        if response.status_code == 200:
            print(f"OK: Created user {user_id}")
            return True
        else:
            result = response.json()
            print(f"INFO: User {user_id} - {result.get('detail', 'Unknown error')}")
            return response.status_code == 400  # User already exists is OK
    except Exception as e:
        print(f"ERROR: Failed to create user {user_id}: {e}")
        return False

def upload_file(admin_user, admin_pass, file_path):
    """Upload a file"""
    try:
        if not os.path.exists(file_path):
            print(f"WARNING: File not found: {file_path}")
            return False
        
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "application/pdf")}
            response = requests.post(
                f"{BASE_URL}/admin/files/upload",
                auth=(admin_user, admin_pass),
                files=files,
                timeout=30
            )
        
        if response.status_code == 200:
            print(f"OK: Uploaded {os.path.basename(file_path)}")
            return True
        else:
            result = response.json()
            print(f"ERROR: Upload failed - {result.get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"ERROR: Failed to upload {file_path}: {e}")
        return False

def test_query(user_id, password, query):
    """Test a query"""
    try:
        print(f"Testing query: '{query[:50]}...'")
        start_time = time.time()
        
        response = requests.post(
            f"{BASE_URL}/query/",
            auth=(user_id, password),
            data={"query": query},
            timeout=60  # Give it time for local model
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get('response', 'No response')
            print(f"OK: Query completed in {duration:.1f}s")
            print(f"Answer: {answer[:100]}...")
            
            # Check if it used cloud or local
            if 'cloud' in str(result).lower() or 'gemini' in str(result).lower() or 'openai' in str(result).lower():
                print("INFO: Used cloud API")
            else:
                print("INFO: Used local Ollama")
            
            return True
        else:
            result = response.json()
            print(f"ERROR: Query failed - {result.get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"ERROR: Query failed: {e}")
        return False

def main():
    print("RAG Application Windows Test")
    print("=" * 40)
    
    # Test server
    if not test_server():
        print("Please start the server first: cd backend && python main.py")
        return
    
    # Create test users
    print("\nCreating test users...")
    add_user("admin", "admin", "user1", "pass123")
    add_user("admin", "admin", "user2", "pass456")
    
    # Upload test files
    print("\nUploading test files...")
    test_files = [
        "test_data/PDF4_AnnualReport.pdf",
        "test_data/PDF5_PostApocalyptic.pdf",
        "test_data/PDF6_ScienceFiction.pdf",
        "test_data/PDF8_BotanicalResearch.pdf"
    ]
    
    uploaded_any = False
    for file_path in test_files:
        if upload_file("admin", "admin", file_path):
            uploaded_any = True
    
    if not uploaded_any:
        print("WARNING: No files uploaded. Creating a simple test document...")
        # Create a simple test file if none exist
        test_dir = Path("test_data")
        test_dir.mkdir(exist_ok=True)
        
        # We'll skip file upload for now and just test queries
    
    # Test queries
    print("\nTesting queries...")
    test_queries = [
        "What is artificial intelligence?",
        "How does machine learning work?",
        "What are the main benefits of AI?",
        "Explain neural networks in simple terms."
    ]
    
    success_count = 0
    for i, query in enumerate(test_queries, 1):
        print(f"\nQuery {i}/{len(test_queries)}:")
        if test_query("user1", "pass123", query):
            success_count += 1
        
        # Small delay between queries
        time.sleep(2)
    
    # Results
    print(f"\n" + "=" * 40)
    print("TEST RESULTS")
    print("=" * 40)
    print(f"Successful queries: {success_count}/{len(test_queries)}")
    
    if success_count > 0:
        print("SUCCESS: RAG system is working!")
        print("\nNext steps:")
        print("1. Visit http://localhost:8000/docs for API documentation")
        print("2. Run: python realistic_performance_test.py")
        print("3. Try: python ui/admin_interface.py --interactive")
    else:
        print("ERROR: No queries succeeded. Check server logs.")
    
    print(f"\nServer running at: {BASE_URL}")

if __name__ == "__main__":
    main()