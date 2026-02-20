#!/bin/bash

# Medrix Project Setup Script
# Sets up both frontend and backend

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Medrix Project Setup               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}\n"

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node -v)
    echo -e "${GREEN}✓ Node.js: $NODE_VERSION${NC}"
else
    echo -e "${RED}✗ Node.js not found${NC}"
    echo -e "${YELLOW}Please install Node.js 18+ from https://nodejs.org/${NC}"
    exit 1
fi

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✓ Python: $PYTHON_VERSION${NC}"
else
    echo -e "${RED}✗ Python3 not found${NC}"
    echo -e "${YELLOW}Please install Python 3.11+ from https://www.python.org/${NC}"
    exit 1
fi

echo ""

# Setup Backend
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}  Setting up Backend (FastAPI)${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}\n"

cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment exists${NC}"
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip install -r requirements.txt > /dev/null 2>&1
echo -e "${GREEN}✓ Python dependencies installed${NC}"

# Check .env
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠ .env file not found${NC}"
    cp .env.example .env
    echo -e "${BLUE}Created .env from template${NC}"
    echo -e "${RED}⚠ IMPORTANT: Edit backend/.env with your Google Cloud credentials!${NC}"
else
    echo -e "${GREEN}✓ .env file exists${NC}"
fi

cd ..

# Setup Frontend
echo -e "\n${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}  Setting up Frontend (Next.js)${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}\n"

cd frontend

# Install npm dependencies
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing npm dependencies...${NC}"
    npm install > /dev/null 2>&1
    echo -e "${GREEN}✓ npm dependencies installed${NC}"
else
    echo -e "${GREEN}✓ node_modules exists${NC}"
fi

# Check .env.local
if [ ! -f ".env.local" ]; then
    echo -e "${YELLOW}⚠ .env.local file not found${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env.local
        echo -e "${BLUE}Created .env.local from template${NC}"
        echo -e "${RED}⚠ IMPORTANT: Edit frontend/.env.local with your database URL!${NC}"
    fi
else
    echo -e "${GREEN}✓ .env.local file exists${NC}"
fi

# Setup database
echo -e "\n${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}  Database Setup${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}\n"

if [ -f ".env.local" ] && grep -q "DATABASE_URL" .env.local; then
    echo -e "${YELLOW}Generating Prisma client...${NC}"
    npx prisma generate > /dev/null 2>&1
    echo -e "${GREEN}✓ Prisma client generated${NC}"
    
    echo -e "${YELLOW}Want to push schema to database? (y/n)${NC}"
    read -r PUSH_DB
    if [ "$PUSH_DB" = "y" ]; then
        npx prisma db push
        echo -e "${GREEN}✓ Database schema pushed${NC}"
    fi
else
    echo -e "${YELLOW}⚠ DATABASE_URL not found in .env.local${NC}"
    echo -e "${BLUE}Skipping database setup${NC}"
fi

cd ..

# Summary
echo -e "\n${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Setup Complete!                    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}\n"

echo -e "${GREEN}✅ Project setup successful!${NC}\n"

echo -e "${BLUE}Next steps:${NC}"
echo -e "  1. Edit ${YELLOW}backend/.env${NC} with your Google Cloud credentials"
echo -e "  2. Edit ${YELLOW}frontend/.env.local${NC} with your database URL"
echo -e "  3. Run backend: ${GREEN}cd backend && ./start.sh${NC}"
echo -e "  4. Run frontend: ${GREEN}cd frontend && npm run dev${NC}"
echo -e "\n${BLUE}Documentation:${NC}"
echo -e "  • Project structure: ${GREEN}PROJECT_STRUCTURE.md${NC}"
echo -e "  • Backend docs: ${GREEN}backend/README.md${NC}"
echo -e "  • API docs: ${GREEN}http://localhost:8000/docs${NC} (after starting backend)"

echo -e "\n${YELLOW}Need help? Check the documentation files!${NC}\n"
