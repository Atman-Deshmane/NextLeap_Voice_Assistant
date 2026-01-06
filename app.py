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
        
        # Get response from LLM (returns dict with text and ui_hint)
        result = engine.chat(user_message)
        
        return jsonify({
            "status": "success",
            "response": result.get("text", ""),
            "ui_component": result.get("ui_hint"),
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


@app.route("/api/voice", methods=["POST"])
def voice():
    """
    Handle voice messages from the frontend.
    
    Request: multipart/form-data with 'audio' file
        
    Response JSON:
        {
            "user_text": "transcribed user speech",
            "agent_text": "agent response",
            "audio_base64": "base64 encoded audio or null",
            "logs": [...]
        }
    """
    try:
        # Check for audio file
        if 'audio' not in request.files:
            return jsonify({
                "status": "error",
                "message": "No audio file provided"
            }), 400
        
        audio_file = request.files['audio']
        
        # Import voice service
        from services import groq_voice
        from services import logger
        
        logger.add_log("🎤 Receiving voice input...", "info")
        
        # Step 1: Transcribe audio (STT)
        logger.add_log("🔊 Transcribing audio with Whisper...", "info")
        user_text = groq_voice.transcribe_audio(audio_file)
        logger.add_log(f"✅ Transcribed: '{user_text[:50]}...'", "success")
        
        # Step 2: Get or create session
        if "session_id" not in session:
            import uuid
            session["session_id"] = str(uuid.uuid4())
        
        session_id = session["session_id"]
        
        if session_id not in _engine_instances:
            _engine_instances[session_id] = LLMEngine()
        
        engine = _engine_instances[session_id]
        
        # Step 3: Process with LLM (returns dict with text and ui_hint)
        logger.add_log("🧠 Processing with AI...", "info")
        result = engine.chat(user_text)
        agent_text = result.get("text", "")
        ui_component = result.get("ui_hint")
        logger.add_log("✅ AI response generated", "success")
        
        # Step 4: Generate speech (TTS) - graceful failure
        logger.add_log("🔊 Generating speech with Orpheus TTS...", "info")
        audio_bytes = groq_voice.generate_audio(agent_text)
        
        audio_base64 = None
        audio_filepath = None
        if audio_bytes:
            audio_base64 = groq_voice.audio_to_base64(audio_bytes)
            logger.add_log("✅ Audio generated successfully", "success")
            
            # Save audio file to disk
            from services import history_manager
            audio_filepath = history_manager.save_audio_file(audio_bytes, session_id)
            if audio_filepath:
                logger.add_log(f"💾 Audio saved: {audio_filepath}", "success")
                # Update session history with audio filepath
                history_manager.update_last_turn_audio(session_id, audio_filepath)
        else:
            logger.add_log("⚠️ TTS unavailable, text-only response", "warning")
        
        return jsonify({
            "status": "success",
            "user_text": user_text,
            "agent_text": agent_text,
            "ui_component": ui_component,
            "audio_base64": audio_base64,
            "audio_file": audio_filepath,
            "logs": g.logs
        })
        
    except Exception as e:
        app.logger.error(f"Error processing voice: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Voice processing error: {str(e)}"
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


# ============================================
# Manual Calendar API Endpoints
# ============================================

@app.route("/api/slots", methods=["GET"])
def get_slots():
    """
    Get slot statuses for a date range.
    
    Query Params:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        
    Returns:
        {"2026-01-07": {"14:00": {"status": "available", "waitlist_count": 0}}}
    """
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        
        if not start_date or not end_date:
            return jsonify({
                "status": "error",
                "message": "start_date and end_date are required"
            }), 400
        
        from services import db_manager
        slots = db_manager.get_slots_with_status(start_date, end_date)
        
        return jsonify({
            "status": "success",
            "slots": slots
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/api/manual/book", methods=["POST"])
def manual_book():
    """
    Book a slot directly (without LLM).
    
    Body: {"date": "...", "time": "...", "topic": "...", "user_alias": "..."}
    """
    try:
        data = request.get_json()
        
        date_str = data.get("date")
        time_str = data.get("time")
        topic = data.get("topic", "General")
        user_alias = data.get("user_alias", "Anonymous")
        
        if not date_str or not time_str:
            return jsonify({
                "status": "error",
                "message": "date and time are required"
            }), 400
        
        from services import db_manager
        result = db_manager.book_slot(date_str, time_str, topic, user_alias)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/api/manual/waitlist", methods=["POST"])
def manual_waitlist():
    """
    Add to waitlist directly (without LLM).
    
    Body: {"date": "...", "time": "...", "topic": "...", "user_alias": "..."}
    """
    try:
        data = request.get_json()
        
        date_str = data.get("date")
        time_str = data.get("time")
        topic = data.get("topic", "General")
        user_alias = data.get("user_alias", "Anonymous")
        
        if not date_str or not time_str:
            return jsonify({
                "status": "error",
                "message": "date and time are required"
            }), 400
        
        from services import db_manager
        result = db_manager.add_to_waitlist(date_str, time_str, topic, user_alias)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/api/booking/lookup", methods=["GET"])
def lookup_booking():
    """Look up a booking or waitlist entry by its code."""
    try:
        booking_code = request.args.get("code")
        
        if not booking_code:
            return jsonify({
                "status": "error",
                "message": "Code is required"
            }), 400
        
        from services import db_manager
        result = db_manager.lookup_any(booking_code.upper())
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/api/booking/modify", methods=["POST"])
def modify_booking():
    """Modify an existing booking."""
    try:
        data = request.get_json()
        
        booking_code = data.get("code")
        new_topic = data.get("topic")
        new_alias = data.get("user_alias")
        
        if not booking_code:
            return jsonify({
                "status": "error",
                "message": "Booking code is required"
            }), 400
        
        from services import db_manager
        result = db_manager.modify_booking(booking_code.upper(), new_topic, new_alias)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/api/booking/reschedule", methods=["POST"])
def reschedule_booking():
    """Reschedule a booking to a new time slot."""
    try:
        data = request.get_json()
        
        booking_code = data.get("code")
        new_date = data.get("date")
        new_time = data.get("time")
        
        if not booking_code or not new_date or not new_time:
            return jsonify({
                "status": "error",
                "message": "code, date, and time are required"
            }), 400
        
        from services import db_manager
        result = db_manager.reschedule_booking(booking_code.upper(), new_date, new_time)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/api/booking/cancel", methods=["POST"])
def cancel_booking_api():
    """Cancel a booking or waitlist entry by its code."""
    try:
        data = request.get_json()
        code = data.get("code")
        entry_type = data.get("type", "booking")  # Can be 'booking' or 'waitlist'
        
        if not code:
            return jsonify({
                "status": "error",
                "message": "Code is required"
            }), 400
        
        from services import db_manager
        
        if entry_type == "waitlist":
            result = db_manager.cancel_waitlist(code.upper())
        else:
            result = db_manager.cancel_booking(code.upper())
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


if __name__ == "__main__":
    # Development server
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    
    print(f"🚀 Starting HDFC Mutual Funds Advisor Scheduler on port {port}")
    print(f"📍 Open http://localhost:{port} in your browser")
    
    app.run(host="0.0.0.0", port=port, debug=debug)
