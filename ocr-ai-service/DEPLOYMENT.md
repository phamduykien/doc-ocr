# 🚀 Hướng dẫn triển khai OCR-AI Service

## 📋 Tổng quan

OCR-AI Service là một microservice độc lập có khả năng:
- **OCR nâng cao**: Tesseract + EasyOCR + PaddleOCR
- **AI Local**: Rule-based + Semantic search + NLP models
- **Chữ viết tay tiếng Việt**: Hỗ trợ đầy đủ
- **Fallback system**: Hoạt động ngay cả thiếu dependencies

## 🛠️ Triển khai Development

### 1. Cài đặt nhanh
```bash
git clone <repository>
cd ocr-ai-service
chmod +x install_dependencies.sh
./install_dependencies.sh
```

### 2. Cấu hình
```bash
cp .env.example .env
# Chỉnh sửa các biến trong .env
```

### 3. Chạy service
```bash
python main.py
```

### 4. Kiểm tra
```bash
# Test cơ bản
python test_api.py

# Test chữ viết tay
python test_handwriting.py
```

## 🐳 Triển khai Docker

### Dockerfile
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-vie \
    tesseract-ocr-eng \
    poppler-utils \
    libopencv-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose
```yaml
version: '3.8'

services:
  ocr-ai-service:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=false
      - LOG_LEVEL=INFO
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Optional: Redis for caching
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped

  # Optional: PostgreSQL for storage
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ocr_ai_db
      POSTGRES_USER: ocr_user
      POSTGRES_PASSWORD: ocr_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

volumes:
  postgres_data:
```

## ☸️ Triển khai Kubernetes

### Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ocr-ai-service
  labels:
    app: ocr-ai-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ocr-ai-service
  template:
    metadata:
      labels:
        app: ocr-ai-service
    spec:
      containers:
      - name: ocr-ai-service
        image: ocr-ai-service:latest
        ports:
        - containerPort: 8000
        env:
        - name: DEBUG
          value: "false"
        - name: LOG_LEVEL
          value: "INFO"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Service
```yaml
apiVersion: v1
kind: Service
metadata:
  name: ocr-ai-service
spec:
  selector:
    app: ocr-ai-service
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: LoadBalancer
```

## 🔧 Cấu hình Production

### Environment Variables
```bash
# Server
DEBUG=false
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# OCR Settings
OCR_DPI=300
OCR_LANG=vie+eng
TESSERACT_CMD=/usr/bin/tesseract

# AI Settings
MIN_CONFIDENCE_SCORE=0.7
AI_MODEL=gpt-3.5-turbo
OPENAI_API_KEY=sk-your-key

# File Settings
MAX_FILE_SIZE=52428800
UPLOAD_DIR=/app/uploads

# Security
ALLOWED_ORIGINS=https://yourdomain.com
API_KEY_HEADER=X-API-Key
```

### Nginx Configuration
```nginx
upstream ocr_ai_backend {
    server ocr-ai-service-1:8000;
    server ocr-ai-service-2:8000;
    server ocr-ai-service-3:8000;
}

server {
    listen 80;
    server_name your-domain.com;
    
    client_max_body_size 50M;
    
    location / {
        proxy_pass http://ocr_ai_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long processing
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 300s;
    }
}
```

## 📊 Monitoring và Logging

### Prometheus Metrics
```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Metrics
REQUESTS_TOTAL = Counter('ocr_requests_total', 'Total OCR requests', ['method', 'endpoint'])
PROCESSING_TIME = Histogram('ocr_processing_seconds', 'Time spent processing documents')
CONFIDENCE_SCORE = Histogram('ocr_confidence_score', 'OCR confidence scores')
ACTIVE_DOCUMENTS = Gauge('ocr_active_documents', 'Currently processing documents')
```

### Logging Configuration
```python
# logging.conf
[loggers]
keys=root,ocr

[handlers]
keys=consoleHandler,fileHandler

[formatters]
keys=simpleFormatter

[logger_root]
level=INFO
handlers=consoleHandler,fileHandler

[logger_ocr]
level=DEBUG
handlers=fileHandler
qualname=ocr
propagate=0

[handler_consoleHandler]
class=StreamHandler
level=INFO
formatter=simpleFormatter
args=(sys.stdout,)

[handler_fileHandler]
class=handlers.RotatingFileHandler
level=DEBUG
formatter=simpleFormatter
args=('logs/ocr-service.log', 'a', 10485760, 5)

[formatter_simpleFormatter]
format=%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

## 🔐 Bảo mật

### API Authentication
```python
# auth.py
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != settings.API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    return credentials.credentials
```

### Rate Limiting
```python
# rate_limit.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.route("/api/v1/documents/process")
@limiter.limit("10/minute")
async def process_document():
    pass
```

## 📈 Performance Tuning

### CPU Optimization
```python
# config/settings.py
import multiprocessing

# Worker processes
WORKERS = multiprocessing.cpu_count()

# OCR threads
OCR_THREADS = min(4, multiprocessing.cpu_count())

# Async settings
ASYNC_POOL_SIZE = 10
```

### Memory Management
```python
# Cleanup old documents
CLEANUP_INTERVAL = 3600  # 1 hour
MAX_DOCUMENT_AGE = 24    # 24 hours
MAX_MEMORY_USAGE = 80    # 80% threshold
```

### Caching Strategy
```python
# Redis caching
REDIS_URL = "redis://localhost:6379"
CACHE_TTL = 3600  # 1 hour
CACHE_OCR_RESULTS = True
CACHE_AI_RESULTS = True
```

## 🧪 Testing Strategy

### Unit Tests
```bash
pytest tests/unit/ -v
```

### Integration Tests
```bash
pytest tests/integration/ -v
```

### Load Testing
```bash
# Using locust
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

### Performance Benchmarks
```bash
# Benchmark script
python tests/benchmark.py
```

## 🚨 Troubleshooting

### Common Issues

1. **OCR Engine Not Found**
   ```bash
   # Check installation
   tesseract --version
   tesseract --list-langs
   ```

2. **Memory Issues**
   ```bash
   # Monitor memory usage
   docker stats ocr-ai-service
   
   # Adjust settings
   OCR_DPI=150  # Reduce quality
   MAX_FILE_SIZE=25M  # Smaller files
   ```

3. **Slow Processing**
   ```bash
   # Enable GPU acceleration
   USE_GPU=true
   
   # Increase workers
   WORKERS=4
   OCR_THREADS=2
   ```

4. **Low Accuracy**
   ```bash
   # Install additional engines
   pip install easyocr paddleocr
   
   # Use higher DPI
   OCR_DPI=400
   
   # Configure OpenAI fallback
   OPENAI_API_KEY=your-key
   ```

## 📞 Support

### Health Checks
- **Service**: `GET /api/v1/health`
- **Dependencies**: `GET /api/v1/config`
- **Statistics**: `GET /api/v1/statistics`

### Monitoring Endpoints
- **Metrics**: `GET /metrics` (Prometheus)
- **Logs**: `/app/logs/ocr-service.log`
- **Status**: `GET /api/v1/status`

### Debugging
```python
# Enable debug mode
DEBUG=true
LOG_LEVEL=DEBUG

# Detailed OCR logging
OCR_DEBUG=true
AI_DEBUG=true
```

Để được hỗ trợ, vui lòng:
1. Kiểm tra logs
2. Chạy health check
3. Cung cấp thông tin môi trường
4. Tạo issue với sample data
