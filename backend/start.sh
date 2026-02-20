#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}🏥 Starting Medrix FastAPI Backend${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found${NC}"
    echo -e "${BLUE}Creating virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}\n"
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source venv/bin/activate

# Check if requirements are installed
if [ ! -f "venv/bin/uvicorn" ]; then
    echo -e "${YELLOW}⚠️  Dependencies not installed${NC}"
    echo -e "${BLUE}Installing requirements...${NC}"
    pip install -r requirements.txt
    echo -e "${GREEN}✓ Dependencies installed${NC}\n"
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo -e "${YELLOW}Please create .env from .env.example and add your credentials${NC}"
    echo -e "${BLUE}Run: cp .env.example .env${NC}\n"
    exit 1
fi

# Start server
echo -e "${GREEN}✓ Starting FastAPI server...${NC}\n"
echo -e "${BLUE}API will be available at:${NC}"
echo -e "  • ${GREEN}http://localhost:8000${NC}"
echo -e "  • ${GREEN}http://localhost:8000/docs${NC} (Interactive API docs)"
echo -e "  • ${GREEN}http://localhost:8000/api/v1${NC} (API v1)"
echo -e "\n${BLUE}Press Ctrl+C to stop${NC}\n"

uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
