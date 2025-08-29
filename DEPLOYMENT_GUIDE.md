# RAG Application Deployment Guide

This guide will walk you through deploying a high-performance RAG (Retrieval-Augmented Generation) application on AWS that can handle 1000+ requests per minute.

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI installed and configured
- Docker installed
- Python 3.11+ installed
- OpenAI API key or Google Gemini API key

## Architecture Overview

```
Internet → ALB → Auto Scaling Group → EC2 Instances → EFS (Persistent Storage)
                                   ↓
                              ChromaDB + Documents
```

## Step 1: Local Setup and Testing

### 1.1 Install Dependencies

```bash
cd rag_project
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

pip install -r backend/requirements.txt
```

### 1.2 Configure Environment

Edit `backend/.env`:
```env
# Add your API keys
OPENAI_API_KEY="your-openai-key-here"
# OR
GOOGLE_API_KEY="your-gemini-key-here"

# Optional: Model configuration
OPENAI_MODEL="gpt-4o"
GEMINI_MODEL="gemini-pro"
```

### 1.3 Test Locally

```bash
# Start the server
cd backend
python main.py

# In another terminal, test the API
cd ..
python client/client.py user-add --admin-user admin --admin-pass admin --new-user user1 --new-pass pass123
python client/client.py upload --user admin --password admin --file "test_data/PDF4_AnnualReport.pdf"
python client/client.py query --user user1 --password pass123 --query "What is in the annual report?"
```

### 1.4 Performance Test Locally

```bash
# Run high-performance load test
python test_performance.py --users 30 --duration 2 --rpm 500 --admin-user admin --admin-pass admin
```

## Step 2: AWS Configuration

### 2.1 Configure AWS CLI

```bash
aws configure
# Enter your credentials:
# AWS Access Key ID: YOUR_ACCESS_KEY
# AWS Secret Access Key: YOUR_SECRET_KEY
# Default region name: ap-south-1
# Default output format: json

# Verify configuration
aws sts get-caller-identity
```

### 2.2 Run AWS Configuration Helper

```bash
cd deploy
python aws_config.py
```

This will:
- Create ECR repository
- Check for existing VPC and EFS
- Generate configuration files
- Create EC2 user data script

## Step 3: Create AWS Infrastructure

### 3.1 Create VPC (if not exists)

1. Go to AWS Console → VPC
2. Click "Create VPC" → "VPC and more"
3. Configure:
   - Name: `rag-app-vpc`
   - IPv4 CIDR: `10.0.0.0/16`
   - AZs: 2
   - Public subnets: 2
   - Private subnets: 2
   - NAT gateways: None (to save costs)
   - Enable DNS hostnames and resolution

### 3.2 Create EFS File System

1. Go to AWS Console → EFS
2. Click "Create file system"
3. Configure:
   - Name: `rag-app-efs`
   - VPC: Select your `rag-app-vpc`
4. Create security group for EFS:
   - Name: `efs-security-group`
   - Inbound rule: NFS (port 2049) from VPC CIDR (10.0.0.0/16)

### 3.3 Create Security Groups

Create security group for EC2 instances:
- Name: `rag-app-sg`
- Inbound rules:
  - HTTP (80) from anywhere
  - Custom TCP (8000) from anywhere
  - SSH (22) from your IP (optional)

## Step 4: Build and Deploy Docker Image

### 4.1 Build and Push Docker Image

```bash
cd deploy
python docker_build.py
```

This will:
- Build the Docker image
- Login to ECR
- Push the image to your ECR repository

### 4.2 Create Launch Template

1. Go to AWS Console → EC2 → Launch Templates
2. Click "Create launch template"
3. Configure:
   - Name: `rag-app-launch-template`
   - AMI: Amazon Linux 2
   - Instance type: `t3.medium`
   - Key pair: Create new or select existing
   - Security groups: Select `rag-app-sg`
   - Storage: 20 GB gp3
   - User data: Copy from generated `ec2_user_data.sh`

## Step 5: Set Up Auto Scaling and Load Balancer

### 5.1 Create Application Load Balancer

1. Go to AWS Console → EC2 → Load Balancers
2. Click "Create Load Balancer" → "Application Load Balancer"
3. Configure:
   - Name: `rag-app-alb`
   - Scheme: Internet-facing
   - VPC: Select your VPC
   - Subnets: Select both public subnets
   - Security group: Select `rag-app-sg`

### 5.2 Create Target Group

1. Go to AWS Console → EC2 → Target Groups
2. Click "Create target group"
3. Configure:
   - Type: Instances
   - Name: `rag-app-targets`
   - Protocol: HTTP, Port: 8000
   - VPC: Select your VPC
   - Health check path: `/docs`

### 5.3 Create Auto Scaling Group

1. Go to AWS Console → EC2 → Auto Scaling Groups
2. Click "Create Auto Scaling group"
3. Configure:
   - Name: `rag-app-asg`
   - Launch template: Select your template
   - VPC: Select your VPC
   - Subnets: Select both public subnets
   - Load balancer: Attach to existing ALB target group
   - Health checks: ELB
   - Group size: Min=1, Desired=2, Max=10
   - Scaling policy: Target tracking (CPU 70%)

## Step 6: Configure Environment Variables

### 6.1 Update Launch Template with API Keys

1. Go to your Launch Template
2. Create new version
3. In User Data, update the environment variables:
   ```bash
   -e OPENAI_API_KEY="your-actual-key" \
   -e GOOGLE_API_KEY="your-actual-key" \
   ```

### 6.2 Update Auto Scaling Group

1. Go to your Auto Scaling Group
2. Edit → Launch template
3. Select the latest version
4. Refresh instances to apply changes

## Step 7: Test Deployment

### 7.1 Get Load Balancer DNS

1. Go to AWS Console → EC2 → Load Balancers
2. Copy the DNS name of your load balancer

### 7.2 Update Client Configuration

Edit `client/client.py`:
```python
BASE_URL = "http://your-load-balancer-dns-name"
```

### 7.3 Upload Test Data

```bash
python client/client.py user-add --admin-user admin --admin-pass admin --new-user user1 --new-pass pass123
python client/client.py upload --user admin --password admin --file "test_data/PDF4_AnnualReport.pdf"
python client/client.py upload --user admin --password admin --file "test_data/PDF5_PostApocalyptic.pdf"
python client/client.py upload --user admin --password admin --file "test_data/PDF6_ScienceFiction.pdf"
python client/client.py upload --user admin --password admin --file "test_data/PDF8_BotanicalResearch.pdf"
```

### 7.4 Run Performance Test

```bash
# Test with 300 users, 1000 RPM for 10 minutes
python test_performance.py \
  --url "http://your-load-balancer-dns-name" \
  --users 300 \
  --duration 10 \
  --rpm 1000 \
  --admin-user admin \
  --admin-pass admin
```

## Step 8: Monitor and Scale

### 8.1 CloudWatch Monitoring

1. Go to AWS Console → CloudWatch
2. Check metrics for:
   - EC2 instances (CPU, memory)
   - Load balancer (request count, latency)
   - Auto Scaling Group (instance count)

### 8.2 Adjust Scaling Policies

Based on performance test results, you may need to:
- Adjust CPU threshold for scaling
- Increase max instance count
- Change instance types (e.g., t3.large for higher load)

## Cost Optimization

### Estimated Costs (10-minute test):
- EC2 instances (2x t3.medium): ~$0.20
- EFS storage: ~$0.01
- Load balancer: ~$0.05
- Data transfer: ~$0.01
- **Total: ~$0.27 for 10 minutes**

### Cost-saving tips:
1. Use Spot instances for non-production
2. Set up proper auto-scaling to minimize idle instances
3. Use EFS Infrequent Access for older documents
4. Monitor and set billing alerts

## Troubleshooting

### Common Issues:

1. **Docker image fails to start**
   - Check CloudWatch logs for the instance
   - Verify EFS mount is successful
   - Ensure API keys are set correctly

2. **High response times**
   - Increase instance size
   - Add more instances to Auto Scaling Group
   - Check EFS performance mode

3. **Rate limiting errors**
   - Increase rate limit in `main.py`
   - Add more instances to distribute load

4. **Memory issues**
   - Use larger instance types
   - Optimize ChromaDB settings
   - Implement document cleanup

### Logs and Debugging:

```bash
# SSH to EC2 instance
ssh -i your-key.pem ec2-user@instance-ip

# Check Docker logs
sudo docker logs rag-app

# Check EFS mount
df -h | grep efs

# Check application files
ls -la /mnt/efs/
```

## Security Considerations

1. **API Keys**: Use AWS Secrets Manager for production
2. **Network**: Use private subnets for EC2 instances
3. **Access**: Implement proper IAM roles and policies
4. **SSL**: Add SSL certificate to load balancer
5. **Authentication**: Consider OAuth2 or JWT tokens

## Next Steps

1. Set up CI/CD pipeline for automated deployments
2. Implement proper logging and monitoring
3. Add SSL/TLS encryption
4. Set up database backups
5. Implement caching layer (Redis/ElastiCache)
6. Add API documentation and versioning

This deployment can handle 1000+ requests per minute with proper scaling and should cost less than $4 for a 10-minute high-load test.