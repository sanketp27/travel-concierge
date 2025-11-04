#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Check if .venv directory exists
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
else
  echo "Virtual environment already exists."
fi

# Activate the virtual environment
# This activation is only for the duration of this script.
. .venv/bin/activate

# # Install requirements
# if [ -f "requirements.txt" ]; then
#   echo "Installing requirements from requirements.txt..."
#   pip install --upgrade pip
#   pip install -r requirements.txt
# else
#   echo "requirements.txt not found! No dependencies will be installed."
# fi

echo "Setup complete."

# Default port
export PORT=${PORT:-8000}

# Load environment variables from config.env
if [ -f "config.env" ]; then
  echo "Loading environment variables from config.env..."
  
  # Filter out comments and blank lines to avoid invalid syntax
  set -a
  grep -v '^[[:space:]]*#' config.env | grep -v '^[[:space:]]*$' > /tmp/clean_env
  . /tmp/clean_env
  set +a
  
  echo "🌐 Starting server on port $PORT..."
  echo "📖 Swagger UI: http://localhost:$PORT/docs"
  echo "📋 OpenAPI: http://localhost:$PORT/openapi.json"
  echo "🔌 API base URL: http://localhost:$PORT"
  echo ""
  echo "Press Ctrl+C to stop the server"
  echo "=================================================="
else
  echo "config.env not found. Skipping environment variable loading."
fi

# Run the app
python3 app.py

echo ""
echo "To activate the virtual environment in your current shell, run:"
echo "source .venv/bin/activate"
