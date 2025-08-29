# High-Performance RAG Application

A production-ready Retrieval-Augmented Generation (RAG) application built with FastAPI, LangChain, and ChromaDB. Supports 1000+ requests per minute with multi-user isolation and AWS deployment.

## 🚀 Features

- **Smart Load Balancing**: Automatically switches between local Ollama and cloud APIs
- **Multi-User Support**: Isolated data and chat history per user
- **Multiple AI Providers**: OpenAI GPT, Google Gemini, and local Ollama
- **Scalable Architecture**: Auto-scaling on AWS with load balancing
- **Persistent Storage**: EFS-based storage for documents and embeddings
- **Rate Limiting**: Configurable request limits per user
- **Chat History**: RAG-enhanced conversation memory
- **Admin Interface**: User and file management APIs
- **Docker Support**: Containerized deployment
- **Realistic Testing**: Performance testing that accounts for hardware limits

## 📋 Requirements

- Python 3.11+
- Docker (for deployment)
- AWS Account (for cloud deployment)
- OpenAI API key or Google Gemini API key

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Load Balancer │────│  Auto Scaling    │────│   EFS Storage   │
│      (ALB)      │    │     Group        │    │  (Documents +   │
└─────────────────┘    └──────────────────┘    │   ChromaDB)     │
                                │               └─────────────────┘
                                ▼
                       ┌──────────────────┐
                       │  EC2 Instances   │
                       │  (FastAPI +      │
                       │   LangChain)     │
                       └──────────────────┘
```

## 🚀 Quick Start

### Local Development

1. **Clone and Setup**
   ```bash
   cd rag_project
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   pip install -r backend/requirements.txt
   ```

2. **Configure Environment**
   ```bash
   # Edit backend/.env
   OPENAI_API_KEY="your-openai-key"
   # OR
   GOOGLE_API_KEY="your-gemini-key"
   ```

3. **Start Server**
   ```bash
   cd backend
   python main.py
   ```

4. **Test the API**
   ```bash
   # Create user and upload documents
   python client/client.py user-add --admin-user admin --admin-pass admin --new-user user1 --new-pass pass123
   python client/client.py upload --user admin --password admin --file "test_data/PDF4_AnnualReport.pdf"
   
   # Query the system
   python client/client.py query --user user1 --password pass123 --query "What is in the annual report?"
   ```

### Using Admin Interface

```bash
# Interactive mode
python ui/admin_interface.py --interactive

# Command line mode
python ui/admin_interface.py --bulk-setup
python ui/admin_interface.py --add-user user1 pass123
python ui/admin_interface.py --upload-dir test_data shared
```

## 🧪 Performance Testing

### Realistic Performance Test (Recommended)
```bash
# Gradual load test that finds your system's limits
python realistic_performance_test.py
```

### Laptop-Friendly Testing
```bash
# Quick test for development laptops
python realistic_performance_test.py --quick
```

### High-Load Testing (Requires Cloud APIs)
```bash
# Only works with OpenAI/Gemini API keys
python test_performance.py --users 300 --duration 10 --rpm 1000
```

### Performance Expectations:
- **Local Ollama Only**: 5-10 RPM max
- **Hybrid Mode**: 50-200 RPM (switches to cloud)
- **Cloud APIs Only**: 1000+ RPM (AWS deployment)

## ☁️ AWS Deployment

### Prerequisites
```bash
# Install AWS CLI and configure
aws configure
aws sts get-caller-identity  # Verify setup
```

### Automated Setup
```bash
cd deploy
python aws_config.py        # Generate AWS configuration
python docker_build.py      # Build and push Docker image
```

### Manual AWS Setup

1. **Create Infrastructure** (see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md))
   - VPC with public/private subnets
   - EFS file system
   - ECR repository
   - Security groups

2. **Deploy Application**
   - Build and push Docker image
   - Create Launch Template
   - Set up Auto Scaling Group
   - Configure Load Balancer

3. **Test Deployment**
   ```bash
   # Update client URL to your load balancer
   python client/client.py query --user user1 --password pass123 --query "Test query"
   
   # Run performance test
   python test_performance.py --url "http://your-alb-dns" --users 300 --rpm 1000
   ```

## 📊 API Endpoints

### Authentication
All endpoints use HTTP Basic Authentication.

### User Management
- `POST /admin/users/add` - Add new user
- `POST /admin/users/remove` - Remove user

### File Management
- `POST /admin/files/upload` - Upload PDF file
- `POST /admin/files/remove` - Remove file

### Query
- `POST /query/` - Send query to RAG system

### Example Usage
```python
import requests

# Add user
response = requests.post(
    "http://localhost:8000/admin/users/add",
    auth=("admin", "admin"),
    data={"user_id": "newuser", "password": "newpass"}
)

# Upload file
with open("document.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/admin/files/upload",
        auth=("admin", "admin"),
        files={"file": f},
        data={"user_id_for_file": "newuser"}
    )

# Query
response = requests.post(
    "http://localhost:8000/query/",
    auth=("newuser", "newpass"),
    data={"query": "What is this document about?"}
)
```

## 🔧 Configuration

### Environment Variables
```env
# AI API Keys
OPENAI_API_KEY="your-openai-key"
GOOGLE_API_KEY="your-gemini-key"

# Model Configuration
OPENAI_MODEL="gpt-4o"
GEMINI_MODEL="gemini-pro"
OLLAMA_MODEL="gemma:2b"

# AWS Configuration
AWS_REGION="ap-south-1"
EFS_FILE_SYSTEM_ID="fs-xxxxxxxxx"
```

### Rate Limiting
Default: 1500 requests per minute per IP. Modify in `main.py`:
```python
@limiter.limit("1500/minute")  # Adjust as needed
```

### Scaling Configuration
- **Min instances**: 1
- **Max instances**: 10
- **Target CPU**: 70%
- **Scale-out cooldown**: 300s
- **Scale-in cooldown**: 300s

## 📁 Project Structure

```
rag_project/
├── backend/                 # FastAPI application
│   ├── main.py             # Main application
│   ├── services.py         # Core services
│   ├── requirements.txt    # Python dependencies
│   ├── Dockerfile          # Container configuration
│   └── .env               # Environment variables
├── client/                 # Client tools
│   └── client.py          # Command-line client
├── ui/                     # User interfaces
│   └── admin_interface.py # Admin interface
├── deploy/                 # Deployment tools
│   ├── aws_config.py      # AWS configuration helper
│   ├── docker_build.py    # Docker build script
│   └── autoscaling_template.json
├── test_data/             # Test documents and questions
├── test_performance.py    # Performance testing tool
├── DEPLOYMENT_GUIDE.md    # Detailed deployment guide
└── README.md             # This file
```

## 🔍 Monitoring and Troubleshooting

### Health Check
```bash
curl http://your-server:8000/docs
```

### Logs
```bash
# Docker logs
docker logs rag-app

# Performance test logs
tail -f performance_test.jsonl
```

### Common Issues

1. **High Response Times**
   - Increase instance size
   - Add more instances
   - Check EFS performance

2. **Rate Limiting**
   - Increase rate limits
   - Add more instances
   - Implement caching

3. **Memory Issues**
   - Use larger instances
   - Optimize ChromaDB settings
   - Implement cleanup

## 💰 Cost Estimation

### 10-minute test (300 users, 1000 RPM):
- EC2 instances (2x t3.medium): ~$0.20
- EFS storage: ~$0.01
- Load balancer: ~$0.05
- Data transfer: ~$0.01
- **Total: ~$0.27**

### Monthly production (moderate load):
- EC2 instances: ~$50-100
- EFS storage: ~$10-20
- Load balancer: ~$20
- **Total: ~$80-140/month**

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
1. Check the [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
2. Review the troubleshooting section
3. Check CloudWatch logs for AWS deployments
4. Open an issue with detailed error information

## 🔮 Roadmap

- [ ] Web UI for administration
- [ ] Redis caching layer
- [ ] Multi-region deployment
- [ ] Advanced analytics
- [ ] API versioning
- [ ] Webhook support
- [ ] Advanced security features