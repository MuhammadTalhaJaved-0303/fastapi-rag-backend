# RAG Application Setup for Laptop (Realistic Performance)

## 🚨 **Reality Check: Local Performance Limits**

Your laptop **CANNOT** handle 1000 requests per minute with local Ollama. Here's what's realistic:

### **Typical Laptop Performance:**
- **CPU-only Gemma 2B**: 2-5 tokens/second
- **Single request**: 10-30 seconds
- **Realistic local throughput**: 2-6 requests per minute
- **For 1000 RPM**: You need cloud APIs (OpenAI/Gemini)

## 💡 **Hybrid Solution: Smart Load Balancing**

The system now automatically switches between:
- **Local Ollama**: For low load (< 10 RPM)
- **Cloud APIs**: For high load (> 10 RPM)

## 🛠️ **Setup Instructions**

### 1. **Install Ollama**

```bash
# Windows: Download from https://ollama.ai
# Or use PowerShell:
winget install Ollama.Ollama

# Pull Gemma 2B model
ollama pull gemma:2b
```

### 2. **Configure Environment**

Edit `backend/.env`:
```env
# For high performance, add cloud API keys
OPENAI_API_KEY="your-openai-key-here"
GOOGLE_API_KEY="your-gemini-key-here"

# Performance settings
USE_CLOUD_FOR_HIGH_LOAD="true"
LOCAL_MAX_RPM="10"  # Max for your laptop
FALLBACK_TO_CLOUD_THRESHOLD="5"

# Ollama optimization for your laptop
OLLAMA_NUM_CTX="1024"  # Smaller context = faster
OLLAMA_NUM_PREDICT="256"  # Shorter responses = faster
```

### 3. **Start the System**

```bash
# Terminal 1: Start Ollama (if not auto-started)
ollama serve

# Terminal 2: Start RAG application
cd rag_project/backend
python main.py
```

### 4. **Test Realistic Performance**

```bash
# Gradual load test (finds your limits)
python realistic_performance_test.py

# Quick test for laptop
python realistic_performance_test.py --quick
```

## 📊 **Expected Performance**

### **Local Only (No API Keys)**
- **Max RPM**: 5-10 requests/minute
- **Response Time**: 10-30 seconds
- **Concurrent Users**: 2-3 max

### **Hybrid Mode (With API Keys)**
- **Low Load**: Uses local Ollama (free)
- **High Load**: Switches to cloud APIs (fast)
- **Max RPM**: 1000+ (limited by API quotas)
- **Response Time**: 1-3 seconds (cloud), 10-30s (local)

## 🎯 **Realistic Testing Scenarios**

### **Scenario 1: Laptop Development**
```bash
# Test with 5 users, 25 RPM for 2 minutes
python realistic_performance_test.py
```
**Expected**: Mostly local Ollama, some cloud fallback

### **Scenario 2: Demo/Presentation**
```bash
# Test with 10 users, 50 RPM for 3 minutes
python realistic_performance_test.py
```
**Expected**: Mix of local and cloud

### **Scenario 3: High Load Simulation**
```bash
# Test with 50 users, 200 RPM for 3 minutes
python realistic_performance_test.py
```
**Expected**: Mostly cloud APIs

## 💰 **Cost Analysis**

### **Local Only**: FREE
- Uses your laptop's CPU
- Very slow but no API costs

### **Hybrid Mode**:
- **Low load**: FREE (local)
- **High load**: ~$0.001-0.01 per request (cloud)
- **1000 requests**: $1-10 depending on model

### **Cloud Only**: $1-10 per 1000 requests
- Fast and scalable
- Costs money but handles any load

## 🔧 **Optimization Tips**

### **For Better Local Performance:**
1. **Close other applications**
2. **Use smaller context window** (`OLLAMA_NUM_CTX="512"`)
3. **Shorter responses** (`OLLAMA_NUM_PREDICT="128"`)
4. **Consider quantized models** (if available)

### **For Cost-Effective Cloud Usage:**
1. **Use Gemini 1.5 Flash** (fastest, cheapest)
2. **Use GPT-4o-mini** (faster than GPT-4o)
3. **Set smart thresholds** to minimize cloud usage

## 🚀 **AWS Deployment (Recommended for 1000 RPM)**

For true 1000 RPM performance, deploy to AWS:

```bash
# Configure AWS
aws configure

# Deploy with cloud APIs
cd deploy
python aws_config.py
python docker_build.py
```

**AWS Performance:**
- **Multiple instances**: Handle any load
- **Auto-scaling**: Scales based on demand
- **Cost**: ~$50-100/month for production

## 📈 **Performance Monitoring**

The system shows real-time stats:
```
[14:30:15] RPM: 45.2, Success: 98.5%, Cloud: 75.0%, Avg: 2.1s
```

- **RPM**: Current requests per minute
- **Success**: Success rate percentage
- **Cloud**: Percentage using cloud APIs
- **Avg**: Average response time

## 🎯 **Realistic Expectations**

### **Your Laptop Can Handle:**
- ✅ Development and testing
- ✅ Small demos (< 10 users)
- ✅ Proof of concept
- ✅ Learning and experimentation

### **Your Laptop Cannot Handle:**
- ❌ 1000 requests per minute locally
- ❌ 300 concurrent users on local model
- ❌ Production workloads without cloud APIs
- ❌ Real-time applications with local model

## 💡 **Recommendations**

### **For Learning/Development:**
- Use local Ollama only
- Test with 2-5 users max
- Focus on functionality over performance

### **For Demos/Presentations:**
- Add Gemini API key (free tier available)
- Test with 10-20 users
- Hybrid mode will impress audiences

### **For Production:**
- Deploy to AWS with auto-scaling
- Use cloud APIs for reliability
- Monitor costs and set limits

## 🆘 **Troubleshooting**

### **Ollama Not Starting:**
```bash
# Check if running
ollama list

# Restart service
ollama serve
```

### **Slow Local Responses:**
- Close other applications
- Reduce context size in `.env`
- Consider using smaller model

### **High API Costs:**
- Increase `LOCAL_MAX_RPM` to use local more
- Increase `FALLBACK_TO_CLOUD_THRESHOLD`
- Monitor usage in cloud provider dashboards

## 🎉 **Success Metrics**

### **Good Performance:**
- Local: 5-10 RPM, 95%+ success rate
- Hybrid: 50+ RPM, 95%+ success rate
- Response times under 5 seconds average

### **Excellent Performance:**
- Hybrid: 200+ RPM, 98%+ success rate
- Smart cloud usage (30-70% cloud)
- Response times under 3 seconds average

Your system is now optimized for realistic laptop performance while maintaining the ability to scale to 1000+ RPM using cloud APIs when needed!