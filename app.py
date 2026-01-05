"""
Flask Application for the HDFC Mutual Funds Advisor Scheduler.
Serves the chat UI and handles API requests.
"""

import os
from flask import Flask, render_template, request, jsonify, session, g
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24).hex())

# Import LLM engine after environment is loaded
from services.llm_engine import LLMEngine

# Store engine instances per session
# Key: session_id (from Flask session), Value: LLMEngine instance
_engine_instances = {}


@app.before_request
def init_logs():
    """Initialize logs for each request."""
    g.logs = []


@app.route("/")
def index():
    """Serve the main chat interface."""
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Handle chat messages from the frontend.
    
    Request JSON:
        {"message": "user message"}
        
    Response JSON:
        {"response": "assistant response", "status": "success"}
    """
    try:
        data = request.get_json()
        
        if not data or "message" not in data:
            return jsonify({
                "status": "error",
                "response": "No message provided"
            }), 400
        
        user_message = data["message"].strip()
        
        if not user_message:
            return jsonify({
                "status": "error",
                "response": "Empty message"
            }), 400
        
        # Get or create session ID
        if "session_id" not in session:
            import uuid
            session["session_id"] = str(uuid.uuid4())
        
        session_id = session["session_id"]
        
        # Get or create engine for this session
        if session_id not in _engine_instances:
            _engine_instances[session_id] = LLMEngine()
        
        engine = _engine_instances[session_id]
        
        # Get response from LLM
        response = engine.chat(user_message)
        
        return jsonify({
            "status": "success",
            "response": response,
            "logs": g.logs  # Include debug logs
        })
        
    except ValueError as e:
        return jsonify({
            "status": "error",
            "response": f"Configuration error: {str(e)}"
        }), 500
    except Exception as e:
        app.logger.error(f"Error processing chat: {str(e)}")
        return jsonify({
            "status": "error",
            "response": "I apologize, but I encountered an error. Please try again."
        }), 500


@app.route("/api/reset", methods=["POST"])
def reset():
    """Reset the conversation history."""
    try:
        if "session_id" in session:
            session_id = session["session_id"]
            # Remove engine instance for this session
            if session_id in _engine_instances:
                del _engine_instances[session_id]
        
        # Clear session
        session.clear()
        
        return jsonify({
            "status": "success",
            "message": "Conversation reset"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "HDFC Mutual Funds Advisor Scheduler"
    })


if __name__ == "__main__":
    # Development server
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    
    print(f"🚀 Starting HDFC Mutual Funds Advisor Scheduler on port {port}")
    print(f"📍 Open http://localhost:{port} in your browser")
    
    app.run(host="0.0.0.0", port=port, debug=debug)
