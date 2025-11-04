#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

echo "=================================================="
echo "🚀 Travel Agent API - Starting..."
echo "=================================================="

# Check if running in container (skip venv creation in container)
if [ -f "/.dockerenv" ]; then
  echo "Running in Docker container, skipping virtual environment setup..."
else
  # Check if .venv directory exists
  if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
  else
    echo "Virtual environment already exists."
  fi

  # Activate the virtual environment
  # This activation is only for the duration of this script.
  echo "Activating virtual environment..."
  . .venv/bin/activate

  # Install requirements
  if [ -f "requirements.txt" ]; then
    echo "Installing requirements from requirements.txt..."
    pip install --no-cache-dir -r requirements.txt
  else
    echo "⚠️  requirements.txt not found! No dependencies will be installed."
  fi
fi

# Set default port
export PORT=${PORT:-8080}

# Load environment variables from config.env
if [ -f "config.env" ]; then
  echo "Loading environment variables from config.env..."
  set -a
  . ./config.env
  set +a
else
  echo "⚠️  config.env not found. Using environment variables only."
fi

echo "=================================================="
echo "✅ Setup complete."
echo "=================================================="
echo "🌐 Starting server on port $PORT..."
echo "📍 API Endpoints:"
echo "   - Health Check:  http://localhost:$PORT/health"
echo "   - Get Session:   http://localhost:$PORT/getSession"
echo "   - Chat:          http://localhost:$PORT/chat"
echo "   - Clear Session: http://localhost:$PORT/clearSession"
echo ""
echo "🔧 Environment: ${ENVIRONMENT:-development}"
echo "🤖 Model: ${GEMINI_MODEL:-gemini-2.0-flash-thinking-exp}"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=================================================="

echo "Starting with Flask development server..."
python3 app.py