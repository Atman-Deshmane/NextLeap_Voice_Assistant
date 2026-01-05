"""
History Manager for the Advisor Scheduler.
Handles session logging and chat history persistence to disk.
"""

import os
import json
from datetime import datetime
from typing import Optional

# Path to history directory
HISTORY_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "history")


def start_session() -> str:
    """
    Start a new chat session.
    
    Creates a unique session ID using timestamp and initializes
    an empty JSON file for the session.
    
    Returns:
        session_id: Unique session identifier (e.g., 'session_20260107_143005')
    """
    # Generate session ID with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"session_{timestamp}"
    
    # Create the session file with empty array
    session_file = os.path.join(HISTORY_DIR, f"{session_id}.json")
    
    # Ensure history directory exists
    os.makedirs(HISTORY_DIR, exist_ok=True)
    
    with open(session_file, 'w') as f:
        json.dump([], f)
    
    return session_id


def log_turn(
    session_id: str, 
    user_text: str, 
    agent_text: str,
    audio_file: Optional[str] = None
) -> bool:
    """
    Log a conversation turn to the session file.
    
    Args:
        session_id: The session identifier
        user_text: The user's message
        agent_text: The agent's response
        audio_file: Optional path to audio file (for future use)
        
    Returns:
        True if logging was successful, False otherwise
    """
    session_file = os.path.join(HISTORY_DIR, f"{session_id}.json")
    
    try:
        # Read existing history
        with open(session_file, 'r') as f:
            history = json.load(f)
        
        # Create new turn entry
        turn = {
            "timestamp": datetime.now().isoformat(),
            "user": user_text,
            "agent": agent_text,
            "audio_file": audio_file  # Placeholder for future audio support
        }
        
        # Append and save
        history.append(turn)
        
        with open(session_file, 'w') as f:
            json.dump(history, f, indent=2)
        
        return True
        
    except FileNotFoundError:
        print(f"Warning: Session file not found for {session_id}")
        return False
    except Exception as e:
        print(f"Error logging turn: {e}")
        return False


def get_session_history(session_id: str) -> list:
    """
    Retrieve the full history for a session.
    
    Args:
        session_id: The session identifier
        
    Returns:
        List of conversation turns
    """
    session_file = os.path.join(HISTORY_DIR, f"{session_id}.json")
    
    try:
        with open(session_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"Error reading session history: {e}")
        return []


def list_sessions() -> list:
    """
    List all available session files.
    
    Returns:
        List of session IDs
    """
    try:
        files = os.listdir(HISTORY_DIR)
        sessions = [f.replace('.json', '') for f in files if f.endswith('.json')]
        return sorted(sessions, reverse=True)  # Most recent first
    except Exception:
        return []
