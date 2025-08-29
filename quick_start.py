#!/usr/bin/env python3
"""
Quick Start Script for RAG Application
Helps set up and test the system step by step
"""

import os
import sys
import subprocess
import time
import requests
from pathlib import Path

def run_command(command: str, cwd: str = None) -> bool:
    """Run a command and return success status"""
    try:
        result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Command failed: {command}")
            print(f"Error: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False

def check_ollama():
    """Check if Ollama is installed and running"""
    print("Checking Ollama...")
    
    # Check if ollama command exists
    if not run_command("ollama --version"):
        print("ERROR: Ollama not found. Please install from https://ollama.ai")
        return False
    
    # Check if ollama is serving
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("OK: Ollama is running")
            
            # Check if gemma:2b is available
            models = response.json().get('models', [])
            gemma_available = any('gemma:2b' in model.get('name', '') for model in models)
            
            if gemma_available:
                print("OK: Gemma 2B model is available")
                return True
            else:
                print("WARNING: Gemma 2B model not found. Pulling...")
                if run_command("ollama pull gemma:2b"):
                    print("OK: Gemma 2B model downloaded")
                    return True
                else:
                    print("ERROR: Failed to download Gemma 2B")
                    return False
        else:
            print("ERROR: Ollama not responding")
            return False
    except:
        print("WARNING: Ollama not running. Starting...")
        # Try to start ollama in background
        if os.name == 'nt':  # Windows
            subprocess.Popen("ollama serve", shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:  # Unix-like
            subprocess.Popen("ollama serve", shell=True)
        
        print("Waiting for Ollama to start...")
        time.sleep(5)
        return check_ollama()  # Recursive check

def check_python_deps():
    """Check if Python dependencies are installed"""
    print("🔍 Checking Python dependencies...")
    
    try:
        import fastapi
        import langchain
        import chromadb
        print("✅ Core dependencies available")
        return True
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("💡 Run: pip install -r backend/requirements.txt")
        return False

def check_api_keys():
    """Check if API keys are configured"""
    print("🔍 Checking API configuration...")
    
    env_file = Path("backend/.env")
    if not env_file.exists():
        print("⚠️  .env file not found")
        return False
    
    with open(env_file, 'r') as f:
        content = f.read()
    
    has_openai = "OPENAI_API_KEY=" in content and not content.split("OPENAI_API_KEY=")[1].split('\n')[0].strip().startswith('#')
    has_gemini = "GOOGLE_API_KEY=" in content and not content.split("GOOGLE_API_KEY=")[1].split('\n')[0].strip().startswith('#')
    
    if has_openai:
        print("✅ OpenAI API key configured")
    if has_gemini:
        print("✅ Gemini API key configured")
    
    if not has_openai and not has_gemini:
        print("⚠️  No cloud API keys configured")
        print("💡 Add your API keys to backend/.env for better performance")
        print("   Local Ollama will be used (slower but free)")
    
    return True

def start_server():
    """Start the FastAPI server"""
    print("🚀 Starting RAG server...")
    
    backend_dir = Path("backend")
    if not backend_dir.exists():
        print("❌ Backend directory not found")
        return None
    
    # Start server in background
    if os.name == 'nt':  # Windows
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=str(backend_dir),
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
    else:  # Unix-like
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=str(backend_dir)
        )
    
    # Wait for server to start
    print("⏳ Waiting for server to start...")
    for i in range(30):  # Wait up to 30 seconds
        try:
            response = requests.get("http://localhost:8000/docs", timeout=2)
            if response.status_code == 200:
                print("✅ Server is running at http://localhost:8000")
                return process
        except:
            pass
        time.sleep(1)
    
    print("❌ Server failed to start")
    return None

def setup_test_data():
    """Set up test users and data"""
    print("📁 Setting up test data...")
    
    try:
        # Use the admin interface for setup
        result = subprocess.run([
            sys.executable, "ui/admin_interface.py", 
            "--bulk-setup",
            "--admin-user", "admin",
            "--admin-pass", "admin"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ Test data setup complete")
            return True
        else:
            print(f"❌ Test data setup failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error setting up test data: {e}")
        return False

def run_quick_test():
    """Run a quick performance test"""
    print("🧪 Running quick performance test...")
    
    try:
        result = subprocess.run([
            sys.executable, "realistic_performance_test.py",
            "--quick"
        ], timeout=120)
        
        if result.returncode == 0:
            print("✅ Quick test completed")
            return True
        else:
            print("❌ Quick test failed")
            return False
    except Exception as e:
        print(f"❌ Error running test: {e}")
        return False

def main():
    print("🚀 RAG Application Quick Start")
    print("=" * 40)
    
    # Check prerequisites
    if not check_python_deps():
        print("\n💡 Install dependencies first:")
        print("   pip install -r backend/requirements.txt")
        return
    
    if not check_ollama():
        print("\n💡 Install and setup Ollama first:")
        print("   1. Download from https://ollama.ai")
        print("   2. Run: ollama pull gemma:2b")
        return
    
    check_api_keys()
    
    # Start the server
    server_process = start_server()
    if not server_process:
        return
    
    try:
        # Setup test data
        if setup_test_data():
            print("\n🎉 Setup complete! You can now:")
            print("   • Visit http://localhost:8000/docs for API documentation")
            print("   • Run: python ui/admin_interface.py --interactive")
            print("   • Run: python realistic_performance_test.py")
            
            # Ask if user wants to run test
            response = input("\n❓ Run a quick performance test now? (y/n): ").strip().lower()
            if response == 'y':
                run_quick_test()
        
        print("\n⏸️  Press Ctrl+C to stop the server")
        
        # Keep server running
        try:
            server_process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Stopping server...")
            server_process.terminate()
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping server...")
        server_process.terminate()

if __name__ == "__main__":
    main()