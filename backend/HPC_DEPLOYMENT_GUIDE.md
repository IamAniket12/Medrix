# MedGemma HPC Deployment Guide

## Quick Start

### 1. Copy Files to HPC
```bash
# Upload these files to your HPC:
# - hpc_medgemma_server.py
# - requirements-hpc.txt
```

### 2. Install Dependencies
```bash
# On your HPC, run:
pip install -r requirements-hpc.txt

# Or install manually:
pip install torch>=2.0.0 transformers>=4.41.0 accelerate>=0.30.0 \
            bitsandbytes pillow fastapi uvicorn[standard] \
            pyngrok httpx python-multipart
```

### 3. Run the Server
```bash
python hpc_medgemma_server.py
```

### 4. Get Your Public URL
The script will:
- Load the MedGemma 1.5 4B model (takes 2-4 minutes first time)
- Start a FastAPI server on port 8000
- Create an ngrok tunnel
- Print the public URL

You'll see output like:
```
======================================================================
🚀 MedGemma HPC Server is LIVE!
📍 Public URL: https://abc123.ngrok-free.app
🏥 Model: google/medgemma-1.5-4b-it
💡 Health check: https://abc123.ngrok-free.app/health
📡 Predict endpoint: https://abc123.ngrok-free.app/predict
======================================================================

⚠️  Copy the Public URL above and set it in your .env file:
   MEDGEMMA_ENDPOINT_URL=https://abc123.ngrok-free.app
```

### 5. Update Your Backend .env
```bash
# In your Medrix backend .env file:
MEDGEMMA_ENDPOINT_URL=https://abc123.ngrok-free.app  # Use the URL printed above
```

### 6. Test the Endpoint
```bash
# On your local machine:
curl https://your-ngrok-url.ngrok-free.app/health
```

## Configuration

### Update Tokens
Edit these lines in `hpc_medgemma_server.py` if needed:
```python
HF_TOKEN = "your_huggingface_token"
NGROK_TOKEN = "your_ngrok_token"
```

### Change Port
Default is 8000. To change:
```python
PORT = 8080  # Or any other port
```

## Requirements

### Hardware
- **GPU**: NVIDIA GPU with CUDA support (12+ GB VRAM recommended)
- **RAM**: 16+ GB
- **Storage**: ~10 GB for model cache

### Software
- Python 3.9+
- CUDA 11.7+ (for GPU acceleration)
- pip or conda

## Troubleshooting

### CUDA Not Available
If you see "CUDA not available", the model will run on CPU (very slow). Make sure:
- Your HPC has GPU nodes
- You're running on a GPU node
- CUDA is properly installed

### Out of Memory
If you get OOM errors:
1. Check available VRAM: `nvidia-smi`
2. Reduce `max_new_tokens` in requests
3. Use a machine with more VRAM

### Ngrok Tunnel Issues
If ngrok fails:
- Check your ngrok token is valid
- You may need to upgrade your ngrok plan for longer sessions
- Try restarting the script

### Model Download Slow
First run downloads ~10GB model:
- Be patient (2-10 minutes depending on HPC network)
- Model is cached for future runs

## Running in Background

### Using screen
```bash
# Start a screen session
screen -S medgemma

# Run the server
python hpc_medgemma_server.py

# Detach: Ctrl+A then D
# Reattach: screen -r medgemma
```

### Using nohup
```bash
nohup python hpc_medgemma_server.py > medgemma.log 2>&1 &

# Check logs
tail -f medgemma.log
```

### Using tmux
```bash
# Start tmux session
tmux new -s medgemma

# Run the server
python hpc_medgemma_server.py

# Detach: Ctrl+B then D
# Reattach: tmux attach -t medgemma
```

## Stopping the Server

### If running in foreground
Press `Ctrl+C`

### If running in background
```bash
# Find the process
ps aux | grep hpc_medgemma_server.py

# Kill it
kill <PID>
```

## Performance Tips

1. **First run**: Model downloads and compiles kernels (5-10 min)
2. **Subsequent runs**: Much faster (<1 min to start)
3. **Inference**: ~5-30 seconds per document depending on complexity
4. **Batch processing**: Process multiple small documents together when possible

## Support

If you encounter issues:
1. Check the logs for error messages
2. Verify GPU is available: `nvidia-smi`
3. Test with a simple request to `/health` endpoint
4. Check ngrok dashboard: https://dashboard.ngrok.com

## API Endpoints

### Health Check
```bash
GET /health

Response:
{
  "status": "ok",
  "model": "google/medgemma-1.5-4b-it",
  "device": "cuda:0"
}
```

### Predict (Document Analysis)
```bash
POST /predict

Body:
{
  "instances": [{
    "image": {"bytesBase64Encoded": "..."},
    "prompt": "Extract medical information from this document"
  }]
}
```

### Predict (Chat/Q&A)
```bash
POST /predict

Body:
{
  "instances": [{
    "@requestFormat": "chatCompletions",
    "messages": [...],
    "max_tokens": 8192,
    "temperature": 0.0
  }]
}
```
