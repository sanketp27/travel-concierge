"""
Flask API for Travel Agent - Cloud Run Ready
Optimized for Google Cloud Run deployment
"""

import os
import sys
import uuid
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from loguru import logger

# Initialize Flask app
app = Flask(__name__)

# App configuration - Cloud Run compatible
APP_NAME = os.getenv("APP_NAME", "Travel Agent API")
PORT = int(os.getenv("PORT", 8080))  # Cloud Run sets PORT env variable
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
ENV = os.getenv("ENVIRONMENT", "production")

# CORS Configuration - More permissive for Cloud Run
ALLOWED_ORIGINS = [
    "https://genaialchemist-frontend-4qcbiz6n2q-uc.a.run.app",
    "https://genaialchemist-frontend-315210470033.us-central1.run.app",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

# Enable CORS - Cloud Run friendly configuration
CORS(app, 
     resources={
         r"/*": {
             "origins": ALLOWED_ORIGINS,
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
             "expose_headers": ["Content-Type", "X-Request-ID"],
             "supports_credentials": True,
             "max_age": 3600
         }
     })

# Import TravelAgent after app initialization
try:
    from src.main_agent import TravelAgent
    logger.info("✅ TravelAgent imported successfully")
except Exception as e:
    logger.error(f"❌ Failed to import TravelAgent: {e}")
    TravelAgent = None


# Middleware for request logging
@app.before_request
def log_request():
    """Log incoming requests"""
    logger.info(f"📥 {request.method} {request.path} - Origin: {request.headers.get('Origin', 'unknown')}")


# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    logger.warning(f"⚠️ 404 Not Found: {request.path}")
    return jsonify({
        "error": "Not Found",
        "message": "The requested endpoint does not exist",
        "path": request.path
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"❌ 500 Internal Error: {str(error)}")
    return jsonify({
        "error": "Internal Server Error",
        "message": "An unexpected error occurred",
        "details": str(error) if DEBUG else None
    }), 500


@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors"""
    logger.warning(f"⚠️ 405 Method Not Allowed: {request.method} {request.path}")
    return jsonify({
        "error": "Method Not Allowed",
        "message": f"The method {request.method} is not allowed for this endpoint"
    }), 405


@app.errorhandler(400)
def bad_request(error):
    """Handle 400 errors"""
    logger.warning(f"⚠️ 400 Bad Request: {str(error)}")
    return jsonify({
        "error": "Bad Request",
        "message": str(error)
    }), 400


# Utility functions
def generate_session_id():
    """Generate a unique session ID."""
    return str(uuid.uuid4())


def validate_request_data(data, required_fields):
    """Validate that required fields are present in request data"""
    if not data:
        return False, "Request body is required"
    
    missing_fields = [field for field in required_fields if not data.get(field)]
    
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    return True, None


def get_request_id():
    """Generate or retrieve request ID for tracing"""
    return request.headers.get('X-Request-ID', str(uuid.uuid4()))


# Routes
@app.route('/', methods=['GET'])
def home():
    """Root endpoint - Health check"""
    return jsonify({
        "status": "healthy",
        "app_name": APP_NAME,
        "environment": ENV,
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "session": "/getSession",
            "chat": "/chat",
            "clear": "/clearSession"
        }
    }), 200


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint for Cloud Run"""
    health_status = {
        "status": "healthy",
        "app_name": APP_NAME,
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "flask": "ok",
            "travel_agent": "ok" if TravelAgent else "error"
        }
    }
    
    status_code = 200 if TravelAgent else 503
    
    if not TravelAgent:
        health_status["status"] = "unhealthy"
        health_status["message"] = "TravelAgent module not available"
    
    return jsonify(health_status), status_code


@app.route('/readiness', methods=['GET'])
def readiness():
    """Readiness probe for Cloud Run"""
    if not TravelAgent:
        return jsonify({
            "status": "not_ready",
            "message": "TravelAgent module not loaded"
        }), 503
    
    return jsonify({
        "status": "ready",
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route('/liveness', methods=['GET'])
def liveness():
    """Liveness probe for Cloud Run"""
    return jsonify({
        "status": "alive",
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route('/getSession', methods=['POST', 'OPTIONS'])
def get_session():
    """
    Generate a new session ID (just a UUID, not initialized yet).
    Session will be initialized on first /chat call.
    Request body: {"user_id": "optional_user_id"}
    """
    # Handle OPTIONS preflight
    if request.method == 'OPTIONS':
        return '', 204
    
    request_id = get_request_id()
    
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', str(uuid.uuid4()))
        
        # Just generate a session ID, don't initialize
        session_id = generate_session_id()
        
        logger.info(f"✅ Session created - ID: {session_id}, User: {user_id}, Request: {request_id}")
        
        return jsonify({
            "session_id": session_id,
            "user_id": user_id,
            "app_name": APP_NAME,
            "message": "Session ID created. Will be initialized on first chat.",
            "request_id": request_id
        }), 201
        
    except Exception as e:
        logger.error(f"❌ Error in get_session: {str(e)}, Request: {request_id}")
        return jsonify({
            "error": "Session Creation Failed",
            "message": "Failed to create session ID",
            "details": str(e) if DEBUG else None,
            "request_id": request_id
        }), 500


@app.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    """
    Main chat endpoint for travel planning.
    Request body: {
        "query": "user's travel query",
        "session_id": "session_id",
        "user_id": "optional_user_id"
    }
    """
    # Handle OPTIONS preflight
    if request.method == 'OPTIONS':
        return '', 204
    
    request_id = get_request_id()
    start_time = datetime.now()
    
    try:
        # Check if TravelAgent is available
        if not TravelAgent:
            logger.error(f"❌ TravelAgent not available, Request: {request_id}")
            return jsonify({
                "error": "Service Unavailable",
                "message": "Travel agent service is not available",
                "request_id": request_id
            }), 503
        
        # Get request data
        data = request.get_json()
        
        # Validate required fields
        is_valid, error_message = validate_request_data(data, ['query', 'session_id'])
        if not is_valid:
            logger.warning(f"⚠️ Validation error: {error_message}, Request: {request_id}")
            return jsonify({
                "error": "Validation Error",
                "message": error_message,
                "request_id": request_id
            }), 400
        
        user_query = data.get('query', '').strip()
        session_id = data.get('session_id')
        user_id = data.get('user_id', 'anonymous')
        
        # Validate query is not empty
        if not user_query:
            return jsonify({
                "error": "Validation Error",
                "message": "Query cannot be empty",
                "request_id": request_id
            }), 400
        
        # Log request
        logger.info(f"📨 Chat request - Session: {session_id}, User: {user_id}, Request: {request_id}")
        logger.info(f"Query: {user_query[:100]}...")
        
        # Create agent and get final response
        agent = TravelAgent(session_id=session_id, user_query=user_query)
        response_text = agent.generate()  # Returns final text directly
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Log successful response
        logger.info(f"✅ Chat response generated - Session: {session_id}, Time: {processing_time:.2f}s, Request: {request_id}")
        
        return jsonify({
            "response": response_text,
            "session_id": session_id,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "processing_time": f"{processing_time:.2f}s",
            "request_id": request_id
        }), 200
        
    except ValueError as e:
        # Handle validation errors
        logger.error(f"⚠️ Validation error in chat: {str(e)}, Request: {request_id}")
        return jsonify({
            "error": "Validation Error",
            "message": str(e),
            "request_id": request_id
        }), 400
        
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"❌ Error in chat endpoint: {str(e)}, Request: {request_id}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "error": "Internal Server Error",
            "message": "An error occurred while processing your request. Please try again.",
            "details": str(e) if DEBUG else None,
            "request_id": request_id
        }), 500


@app.route('/clearSession', methods=['POST', 'OPTIONS'])
def clear_session():
    """
    Clear a session's chat history.
    Request body: {"session_id": "session_id"}
    """
    # Handle OPTIONS preflight
    if request.method == 'OPTIONS':
        return '', 204
    
    request_id = get_request_id()
    
    try:
        data = request.get_json()
        
        # Validate required fields
        is_valid, error_message = validate_request_data(data, ['session_id'])
        if not is_valid:
            return jsonify({
                "error": "Validation Error",
                "message": error_message,
                "request_id": request_id
            }), 400
        
        session_id = data.get('session_id')
        
        # Import cache to clear session
        from src.chat_history import SQLCache
        cache = SQLCache(session_id=session_id, context="travel_agent")
        
        # Clear session data
        cache.clear_session(session_id)
        
        logger.info(f"🗑️ Session cleared: {session_id}, Request: {request_id}")
        
        return jsonify({
            "message": "Session cleared successfully",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error clearing session: {str(e)}, Request: {request_id}")
        return jsonify({
            "error": "Internal Server Error",
            "message": "Failed to clear session",
            "details": str(e) if DEBUG else None,
            "request_id": request_id
        }), 500


# Additional OPTIONS handler for all routes
@app.after_request
def after_request(response):
    """Add CORS headers to all responses - Cloud Run compatible"""
    origin = request.headers.get('Origin')
    
    # Allow configured origins
    if origin in ALLOWED_ORIGINS:
        response.headers['Access-Control-Allow-Origin'] = origin
    elif ENV == 'development':
        # In development, allow all origins
        response.headers['Access-Control-Allow-Origin'] = '*'
    
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, X-Request-ID'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Max-Age'] = '3600'
    response.headers['Access-Control-Expose-Headers'] = 'Content-Type, X-Request-ID'
    
    # Add request ID to response
    request_id = get_request_id()
    response.headers['X-Request-ID'] = request_id
    
    return response



# Run the application
if __name__ == '__main__':
    logger.info(f"🌐 Starting {APP_NAME} on 0.0.0.0:{PORT}")
    
    # Cloud Run expects the app to listen on 0.0.0.0
    app.run(
        host='0.0.0.0',
        port=PORT,
        debug=DEBUG,
        threaded=True  # Enable threading for concurrent requests
    )