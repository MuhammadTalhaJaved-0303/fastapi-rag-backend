#!/usr/bin/env python3
"""
Docker Build and Push Script for RAG Application
"""

import os
import json
import subprocess
import sys
from pathlib import Path

def run_command(command: str, cwd: str = None) -> bool:
    """Run a shell command and return success status"""
    print(f"Running: {command}")
    try:
        result = subprocess.run(command, shell=True, cwd=cwd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        return False

def load_config(config_file: str = "aws_deployment_config.json") -> dict:
    """Load AWS deployment configuration"""
    if not os.path.exists(config_file):
        print(f"Configuration file {config_file} not found.")
        print("Please run aws_config.py first to generate the configuration.")
        sys.exit(1)
    
    with open(config_file, 'r') as f:
        return json.load(f)

def build_and_push_docker_image():
    """Build and push Docker image to ECR"""
    # Load configuration
    config = load_config()
    
    ecr_uri = config.get('ecr_repository_uri')
    region = config.get('region')
    
    if not ecr_uri:
        print("ECR repository URI not found in configuration.")
        sys.exit(1)
    
    # Change to backend directory
    backend_dir = Path(__file__).parent.parent / "backend"
    if not backend_dir.exists():
        print(f"Backend directory not found: {backend_dir}")
        sys.exit(1)
    
    print(f"Building Docker image in: {backend_dir}")
    
    # Build Docker image
    build_command = f"docker build -t {ecr_uri}:latest ."
    if not run_command(build_command, str(backend_dir)):
        print("Docker build failed!")
        sys.exit(1)
    
    # Login to ECR
    login_command = f"aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin {ecr_uri}"
    if not run_command(login_command):
        print("ECR login failed!")
        sys.exit(1)
    
    # Push image
    push_command = f"docker push {ecr_uri}:latest"
    if not run_command(push_command):
        print("Docker push failed!")
        sys.exit(1)
    
    print("Docker image built and pushed successfully!")
    print(f"Image URI: {ecr_uri}:latest")

def main():
    print("Docker Build and Push Script")
    print("=" * 30)
    
    # Check if Docker is running
    if not run_command("docker --version"):
        print("Docker is not installed or not running.")
        sys.exit(1)
    
    # Check if AWS CLI is configured
    if not run_command("aws sts get-caller-identity"):
        print("AWS CLI is not configured. Please run 'aws configure' first.")
        sys.exit(1)
    
    build_and_push_docker_image()

if __name__ == "__main__":
    main()