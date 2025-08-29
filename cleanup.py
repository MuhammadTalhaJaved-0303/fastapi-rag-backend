#!/usr/bin/env python3
"""
Cleanup script for RAG application
Removes test users, files, and resets the database
"""

import os
import shutil
import json
import argparse
from pathlib import Path

def cleanup_local_data():
    """Clean up local EFS data"""
    efs_path = Path("efs")
    
    if efs_path.exists():
        print("Cleaning up local EFS data...")
        
        # Remove ChromaDB data
        chroma_path = efs_path / "chroma_db"
        if chroma_path.exists():
            shutil.rmtree(chroma_path)
            print("  ✓ Removed ChromaDB data")
        
        # Remove documents
        docs_path = efs_path / "documents"
        if docs_path.exists():
            shutil.rmtree(docs_path)
            print("  ✓ Removed documents")
        
        # Remove user database
        user_db_path = efs_path / "user_db.json"
        if user_db_path.exists():
            user_db_path.unlink()
            print("  ✓ Removed user database")
        
        # Recreate directory structure
        os.makedirs(chroma_path, exist_ok=True)
        os.makedirs(docs_path / "shared", exist_ok=True)
        os.makedirs(docs_path / "users", exist_ok=True)
        print("  ✓ Recreated directory structure")
    
    # Clean up backend EFS data
    backend_efs_path = Path("backend/efs")
    if backend_efs_path.exists():
        print("Cleaning up backend EFS data...")
        shutil.rmtree(backend_efs_path)
        print("  ✓ Removed backend EFS data")

def cleanup_log_files():
    """Clean up log files"""
    log_files = [
        "log.jsonl",
        "query_log.txt",
        "server_log.txt",
        "performance_test.jsonl"
    ]
    
    print("Cleaning up log files...")
    for log_file in log_files:
        if os.path.exists(log_file):
            os.remove(log_file)
            print(f"  ✓ Removed {log_file}")

def cleanup_test_users(base_url: str = "http://127.0.0.1:8000", admin_user: str = "admin", admin_pass: str = "admin"):
    """Remove test users via API"""
    try:
        import requests
        
        print("Cleaning up test users via API...")
        
        # Common test user patterns
        test_user_patterns = [
            "user1", "user2", "user3",
            "testuser", "test_user",
            "loadtest_user_", "perf_user_"
        ]
        
        for pattern in test_user_patterns:
            if pattern.endswith("_"):
                # Pattern with numbers
                for i in range(100):  # Check up to 100 numbered users
                    user_id = f"{pattern}{i}"
                    try:
                        response = requests.post(
                            f"{base_url}/admin/users/remove",
                            auth=(admin_user, admin_pass),
                            data={"user_id_to_remove": user_id},
                            timeout=5
                        )
                        if response.status_code == 200:
                            print(f"  ✓ Removed user {user_id}")
                    except:
                        pass  # User doesn't exist or server not running
            else:
                # Single user
                try:
                    response = requests.post(
                        f"{base_url}/admin/users/remove",
                        auth=(admin_user, admin_pass),
                        data={"user_id_to_remove": pattern},
                        timeout=5
                    )
                    if response.status_code == 200:
                        print(f"  ✓ Removed user {pattern}")
                except:
                    pass  # User doesn't exist or server not running
    
    except ImportError:
        print("  ⚠ requests library not available, skipping API cleanup")
    except Exception as e:
        print(f"  ⚠ API cleanup failed: {e}")

def cleanup_docker():
    """Clean up Docker containers and images"""
    try:
        import subprocess
        
        print("Cleaning up Docker resources...")
        
        # Stop and remove RAG app container
        try:
            subprocess.run(["docker", "stop", "rag-app"], capture_output=True)
            subprocess.run(["docker", "rm", "rag-app"], capture_output=True)
            print("  ✓ Removed rag-app container")
        except:
            pass
        
        # Remove unused images (optional)
        try:
            result = subprocess.run(["docker", "image", "prune", "-f"], capture_output=True, text=True)
            if result.returncode == 0:
                print("  ✓ Cleaned up unused Docker images")
        except:
            pass
    
    except Exception as e:
        print(f"  ⚠ Docker cleanup failed: {e}")

def main():
    parser = argparse.ArgumentParser(description="Cleanup RAG application data")
    parser.add_argument("--all", action="store_true", help="Clean up everything")
    parser.add_argument("--data", action="store_true", help="Clean up local data only")
    parser.add_argument("--logs", action="store_true", help="Clean up log files only")
    parser.add_argument("--users", action="store_true", help="Clean up test users via API")
    parser.add_argument("--docker", action="store_true", help="Clean up Docker resources")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="API base URL")
    parser.add_argument("--admin-user", default="admin", help="Admin username")
    parser.add_argument("--admin-pass", default="admin", help="Admin password")
    
    args = parser.parse_args()
    
    if not any([args.all, args.data, args.logs, args.users, args.docker]):
        print("No cleanup option specified. Use --help for options.")
        return
    
    print("RAG Application Cleanup")
    print("=" * 30)
    
    if args.all or args.data:
        cleanup_local_data()
    
    if args.all or args.logs:
        cleanup_log_files()
    
    if args.all or args.users:
        cleanup_test_users(args.url, args.admin_user, args.admin_pass)
    
    if args.all or args.docker:
        cleanup_docker()
    
    print("\nCleanup complete!")
    print("\nTo start fresh:")
    print("1. cd backend && python main.py")
    print("2. python ui/admin_interface.py --bulk-setup")

if __name__ == "__main__":
    main()