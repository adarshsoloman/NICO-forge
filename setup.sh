#!/bin/bash

# NICO-Forge Setup Script for Linux/macOS

set -e  # Exit on error

echo "🔥 NICO-Forge Setup"
echo "==================="
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3."
    exit 1
fi

PYTHON_CMD="python3"
echo "✓ Python 3 found"

# Check for uv (optional but recommended)
USE_UV=false
if command -v uv &> /dev/null; then
    echo "✓ uv found (using for faster installation)"
    USE_UV=true
else
    echo "ℹ️  uv not found (falling back to standard pip)"
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ -d ".venv" ]; then
    echo "ℹ️  .venv already exists"
else
    if [ "$USE_UV" = true ]; then
        uv venv .venv
    else
        $PYTHON_CMD -m venv .venv
    fi
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
if [ "$USE_UV" = true ]; then
    uv pip install -r requirements.txt
else
    pip install --upgrade pip
    pip install -r requirements.txt
fi
echo "✓ Dependencies installed"

# Create .env from template
echo ""
echo "Setting up environment file..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✓ Created .env file"
    echo "⚠️  IMPORTANT: Edit .env and add your OPENROUTER_API_KEY"
else
    echo "✓ .env file already exists"
fi

# Create test data
echo ""
echo "Creating test data..."
python create_test_data.py
echo "✓ Test data created"

echo ""
echo "==================================="
echo "✓ Setup complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "1. Edit .env and add your API keys"
echo "2. Activate the environment:"
echo "   source .venv/bin/activate"
echo "3. Run the pipeline:"
echo "   python main.py test_data/sample_healthcare_en.txt"
echo ""
