#!/usr/bin/env python3
"""
Simple Admin Interface for RAG Application
Provides a command-line interface for managing users and files
"""

import os
import sys
import requests
import json
from typing import List, Dict, Any
import argparse
from pathlib import Path

class RAGAdminInterface:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip('/')
        self.admin_user = None
        self.admin_pass = None
    
    def authenticate(self, username: str, password: str) -> bool:
        """Test authentication with the server"""
        try:
            response = requests.post(
                f"{self.base_url}/admin/users/add",
                auth=(username, password),
                data={"user_id": "test_auth", "password": "test"}
            )
            # If we get a 400 (user exists) or 200, auth is good
            if response.status_code in [200, 400]:
                self.admin_user = username
                self.admin_pass = password
                # Clean up test user if created
                if response.status_code == 200:
                    self.remove_user("test_auth")
                return True
            return False
        except Exception as e:
            print(f"Authentication failed: {e}")
            return False
    
    def add_user(self, user_id: str, password: str) -> Dict[str, Any]:
        """Add a new user"""
        try:
            response = requests.post(
                f"{self.base_url}/admin/users/add",
                auth=(self.admin_user, self.admin_pass),
                data={"user_id": user_id, "password": password}
            )
            return {"success": response.status_code == 200, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def remove_user(self, user_id: str) -> Dict[str, Any]:
        """Remove a user"""
        try:
            response = requests.post(
                f"{self.base_url}/admin/users/remove",
                auth=(self.admin_user, self.admin_pass),
                data={"user_id_to_remove": user_id}
            )
            return {"success": response.status_code == 200, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def upload_file(self, file_path: str, user_id: str = None) -> Dict[str, Any]:
        """Upload a file"""
        try:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f, "application/pdf")}
                data = {"user_id_for_file": user_id} if user_id else {}
                response = requests.post(
                    f"{self.base_url}/admin/files/upload",
                    auth=(self.admin_user, self.admin_pass),
                    files=files,
                    data=data
                )
            return {"success": response.status_code == 200, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def upload_directory(self, dir_path: str, user_id: str = None) -> List[Dict[str, Any]]:
        """Upload all PDF files from a directory"""
        results = []
        dir_path = Path(dir_path)
        
        if not dir_path.exists():
            return [{"success": False, "error": f"Directory not found: {dir_path}"}]
        
        pdf_files = list(dir_path.glob("*.pdf"))
        if not pdf_files:
            return [{"success": False, "error": f"No PDF files found in {dir_path}"}]
        
        for pdf_file in pdf_files:
            print(f"Uploading {pdf_file.name}...")
            result = self.upload_file(str(pdf_file), user_id)
            result["file"] = pdf_file.name
            results.append(result)
        
        return results
    
    def remove_file(self, file_name: str, user_id: str = None) -> Dict[str, Any]:
        """Remove a file"""
        try:
            data = {"file_name": file_name}
            if user_id:
                data["user_id_for_file"] = user_id
            
            response = requests.post(
                f"{self.base_url}/admin/files/remove",
                auth=(self.admin_user, self.admin_pass),
                data=data
            )
            return {"success": response.status_code == 200, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def query(self, user_id: str, password: str, query: str, conversation_id: str = None) -> Dict[str, Any]:
        """Send a query"""
        try:
            data = {"query": query}
            if conversation_id:
                data["conversation_id"] = conversation_id
            
            response = requests.post(
                f"{self.base_url}/query/",
                auth=(user_id, password),
                data=data
            )
            return {"success": response.status_code == 200, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def interactive_mode(self):
        """Run interactive mode"""
        print("RAG Admin Interface - Interactive Mode")
        print("=" * 40)
        
        while True:
            print("\nAvailable commands:")
            print("1. Add user")
            print("2. Remove user")
            print("3. Upload file")
            print("4. Upload directory")
            print("5. Remove file")
            print("6. Test query")
            print("7. Bulk setup (create users + upload files)")
            print("8. Exit")
            
            choice = input("\nEnter your choice (1-8): ").strip()
            
            if choice == "1":
                user_id = input("Enter user ID: ").strip()
                password = input("Enter password: ").strip()
                result = self.add_user(user_id, password)
                print(f"Result: {result}")
            
            elif choice == "2":
                user_id = input("Enter user ID to remove: ").strip()
                result = self.remove_user(user_id)
                print(f"Result: {result}")
            
            elif choice == "3":
                file_path = input("Enter file path: ").strip()
                user_id = input("Enter user ID (or press Enter for shared): ").strip()
                user_id = user_id if user_id else None
                result = self.upload_file(file_path, user_id)
                print(f"Result: {result}")
            
            elif choice == "4":
                dir_path = input("Enter directory path: ").strip()
                user_id = input("Enter user ID (or press Enter for shared): ").strip()
                user_id = user_id if user_id else None
                results = self.upload_directory(dir_path, user_id)
                for result in results:
                    print(f"File {result.get('file', 'unknown')}: {result}")
            
            elif choice == "5":
                file_name = input("Enter file name: ").strip()
                user_id = input("Enter user ID (or press Enter for shared): ").strip()
                user_id = user_id if user_id else None
                result = self.remove_file(file_name, user_id)
                print(f"Result: {result}")
            
            elif choice == "6":
                user_id = input("Enter user ID: ").strip()
                password = input("Enter password: ").strip()
                query_text = input("Enter query: ").strip()
                conversation_id = input("Enter conversation ID (optional): ").strip()
                conversation_id = conversation_id if conversation_id else None
                result = self.query(user_id, password, query_text, conversation_id)
                if result["success"]:
                    data = result["data"]
                    print(f"\nResponse: {data.get('response', 'No response')}")
                    print(f"Sources: {len(data.get('source_documents', []))} documents")
                else:
                    print(f"Error: {result}")
            
            elif choice == "7":
                self.bulk_setup()
            
            elif choice == "8":
                print("Goodbye!")
                break
            
            else:
                print("Invalid choice. Please try again.")
    
    def bulk_setup(self):
        """Set up multiple users and upload test files"""
        print("\nBulk Setup - Creating test environment")
        print("-" * 40)
        
        # Create test users
        test_users = [
            ("user1", "pass123"),
            ("user2", "pass456"),
            ("testuser", "test123")
        ]
        
        print("Creating test users...")
        for user_id, password in test_users:
            result = self.add_user(user_id, password)
            status = "OK" if result["success"] else "FAIL"
            print(f"  {status} {user_id}")
        
        # Upload shared files
        test_data_dir = Path("test_data")
        if test_data_dir.exists():
            print("\nUploading shared files...")
            results = self.upload_directory(str(test_data_dir))
            for result in results:
                status = "OK" if result["success"] else "FAIL"
                print(f"  {status} {result.get('file', 'unknown')}")
        
        # Upload user-specific files
        for user_id, _ in test_users[:2]:  # Only for first 2 users
            user_dir = test_data_dir / "pdfs" / user_id
            if user_dir.exists():
                print(f"\nUploading files for {user_id}...")
                results = self.upload_directory(str(user_dir), user_id)
                for result in results:
                    status = "OK" if result["success"] else "FAIL"
                    print(f"  {status} {result.get('file', 'unknown')}")
        
        print("\nBulk setup complete!")
        print("You can now test queries with:")
        print("  User: user1, Password: pass123")
        print("  User: user2, Password: pass456")

def main():
    parser = argparse.ArgumentParser(description="RAG Admin Interface")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Base URL of RAG API")
    parser.add_argument("--admin-user", help="Admin username")
    parser.add_argument("--admin-pass", help="Admin password")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    
    # Command-specific arguments
    parser.add_argument("--add-user", nargs=2, metavar=("USER_ID", "PASSWORD"), help="Add user")
    parser.add_argument("--remove-user", metavar="USER_ID", help="Remove user")
    parser.add_argument("--upload-file", nargs=2, metavar=("FILE_PATH", "USER_ID"), help="Upload file")
    parser.add_argument("--upload-dir", nargs=2, metavar=("DIR_PATH", "USER_ID"), help="Upload directory")
    parser.add_argument("--remove-file", nargs=2, metavar=("FILE_NAME", "USER_ID"), help="Remove file")
    parser.add_argument("--bulk-setup", action="store_true", help="Run bulk setup")
    
    args = parser.parse_args()
    
    # Create interface
    interface = RAGAdminInterface(args.url)
    
    # Get admin credentials
    admin_user = args.admin_user or input("Admin username: ")
    admin_pass = args.admin_pass or input("Admin password: ")
    
    # Authenticate
    if not interface.authenticate(admin_user, admin_pass):
        print("Authentication failed!")
        sys.exit(1)
    
    print(f"Authenticated as {admin_user}")
    
    # Execute commands
    if args.interactive:
        interface.interactive_mode()
    elif args.add_user:
        result = interface.add_user(args.add_user[0], args.add_user[1])
        print(json.dumps(result, indent=2))
    elif args.remove_user:
        result = interface.remove_user(args.remove_user)
        print(json.dumps(result, indent=2))
    elif args.upload_file:
        user_id = args.upload_file[1] if args.upload_file[1] != "shared" else None
        result = interface.upload_file(args.upload_file[0], user_id)
        print(json.dumps(result, indent=2))
    elif args.upload_dir:
        user_id = args.upload_dir[1] if args.upload_dir[1] != "shared" else None
        results = interface.upload_directory(args.upload_dir[0], user_id)
        print(json.dumps(results, indent=2))
    elif args.remove_file:
        user_id = args.remove_file[1] if args.remove_file[1] != "shared" else None
        result = interface.remove_file(args.remove_file[0], user_id)
        print(json.dumps(result, indent=2))
    elif args.bulk_setup:
        interface.bulk_setup()
    else:
        print("No command specified. Use --interactive for interactive mode or --help for options.")

if __name__ == "__main__":
    main()