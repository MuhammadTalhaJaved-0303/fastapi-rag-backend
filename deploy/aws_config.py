#!/usr/bin/env python3
"""
AWS Configuration and Deployment Helper
This script helps configure AWS resources for the RAG application
"""

import os
import json
import boto3
import subprocess
from typing import Dict, Any

class AWSConfig:
    def __init__(self, region: str = "ap-south-1"):
        self.region = region
        self.session = boto3.Session(region_name=region)
        self.ec2 = self.session.client('ec2')
        self.ecs = self.session.client('ecs')
        self.ecr = self.session.client('ecr')
        self.efs = self.session.client('efs')
        
    def get_account_id(self) -> str:
        """Get AWS account ID"""
        sts = self.session.client('sts')
        return sts.get_caller_identity()['Account']
    
    def create_ecr_repository(self, repo_name: str = "rag-agent-repo") -> str:
        """Create ECR repository if it doesn't exist"""
        try:
            response = self.ecr.describe_repositories(repositoryNames=[repo_name])
            repo_uri = response['repositories'][0]['repositoryUri']
            print(f"ECR repository already exists: {repo_uri}")
            return repo_uri
        except self.ecr.exceptions.RepositoryNotFoundException:
            print(f"Creating ECR repository: {repo_name}")
            response = self.ecr.create_repository(repositoryName=repo_name)
            repo_uri = response['repository']['repositoryUri']
            print(f"Created ECR repository: {repo_uri}")
            return repo_uri
    
    def get_or_create_vpc(self, vpc_name: str = "rag-app-vpc") -> Dict[str, Any]:
        """Get existing VPC or provide creation instructions"""
        vpcs = self.ec2.describe_vpcs(
            Filters=[{'Name': 'tag:Name', 'Values': [vpc_name]}]
        )
        
        if vpcs['Vpcs']:
            vpc = vpcs['Vpcs'][0]
            print(f"Found existing VPC: {vpc['VpcId']}")
            return {
                'vpc_id': vpc['VpcId'],
                'cidr_block': vpc['CidrBlock']
            }
        else:
            print(f"VPC '{vpc_name}' not found. Please create it manually using the AWS Console.")
            return {}
    
    def get_efs_file_system(self, efs_name: str = "rag-app-efs") -> str:
        """Get EFS file system ID"""
        file_systems = self.efs.describe_file_systems()
        
        for fs in file_systems['FileSystems']:
            tags = self.efs.describe_tags(FileSystemId=fs['FileSystemId'])
            for tag in tags['Tags']:
                if tag['Key'] == 'Name' and tag['Value'] == efs_name:
                    print(f"Found EFS: {fs['FileSystemId']}")
                    return fs['FileSystemId']
        
        print(f"EFS '{efs_name}' not found. Please create it manually.")
        return ""
    
    def generate_user_data_script(self, ecr_uri: str, efs_id: str, openai_key: str = "", gemini_key: str = "") -> str:
        """Generate EC2 user data script"""
        account_id = self.get_account_id()
        
        script = f"""#!/bin/bash
yum update -y
yum install -y docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install EFS utilities
yum install -y amazon-efs-utils

# Create mount point
mkdir -p /mnt/efs

# Mount EFS
mount -t efs {efs_id}:/ /mnt/efs

# Add to fstab for persistence
echo "{efs_id}:/ /mnt/efs efs defaults,_netdev 0 0" >> /etc/fstab

# Login to ECR
aws ecr get-login-password --region {self.region} | docker login --username AWS --password-stdin {account_id}.dkr.ecr.{self.region}.amazonaws.com

# Pull Docker image
docker pull {ecr_uri}:latest

# Create application directories
mkdir -p /mnt/efs/chroma_db
mkdir -p /mnt/efs/documents/shared
mkdir -p /mnt/efs/documents/users

# Start RAG application
docker run -d \\
  --name rag-app \\
  -p 8000:8000 \\
  -v /mnt/efs:/app/efs \\
  -e OPENAI_API_KEY="{openai_key}" \\
  -e GOOGLE_API_KEY="{gemini_key}" \\
  --restart unless-stopped \\
  {ecr_uri}:latest
"""
        return script
    
    def save_config(self, config: Dict[str, Any], filename: str = "aws_deployment_config.json"):
        """Save configuration to file"""
        with open(filename, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"Configuration saved to {filename}")

def main():
    print("AWS RAG Application Configuration Helper")
    print("=" * 50)
    
    # Initialize AWS config
    aws_config = AWSConfig()
    
    try:
        account_id = aws_config.get_account_id()
        print(f"AWS Account ID: {account_id}")
        print(f"Region: {aws_config.region}")
    except Exception as e:
        print(f"Error: Unable to connect to AWS. Please run 'aws configure' first.")
        print(f"Details: {e}")
        return
    
    # Create ECR repository
    ecr_uri = aws_config.create_ecr_repository()
    
    # Get VPC info
    vpc_info = aws_config.get_or_create_vpc()
    
    # Get EFS info
    efs_id = aws_config.get_efs_file_system()
    
    # Generate configuration
    config = {
        "account_id": account_id,
        "region": aws_config.region,
        "ecr_repository_uri": ecr_uri,
        "vpc_info": vpc_info,
        "efs_file_system_id": efs_id,
        "docker_build_command": f"docker build -t {ecr_uri}:latest .",
        "docker_push_commands": [
            f"aws ecr get-login-password --region {aws_config.region} | docker login --username AWS --password-stdin {ecr_uri}",
            f"docker push {ecr_uri}:latest"
        ]
    }
    
    # Save configuration
    aws_config.save_config(config)
    
    # Generate user data script
    openai_key = input("Enter your OpenAI API key (or press Enter to skip): ").strip()
    gemini_key = input("Enter your Gemini API key (or press Enter to skip): ").strip()
    
    if efs_id:
        user_data = aws_config.generate_user_data_script(ecr_uri, efs_id, openai_key, gemini_key)
        with open("ec2_user_data.sh", "w") as f:
            f.write(user_data)
        print("EC2 user data script saved to ec2_user_data.sh")
    
    print("\nNext steps:")
    print("1. Build and push your Docker image using the commands in the config file")
    print("2. Create your VPC and EFS if they don't exist")
    print("3. Use the generated user data script when launching EC2 instances")

if __name__ == "__main__":
    main()