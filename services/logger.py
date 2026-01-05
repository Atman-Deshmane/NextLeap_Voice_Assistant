"""
Logger Service for the Advisor Scheduler.
Provides request-scoped logging for transparency and debugging.
"""

from datetime import datetime
from typing import Optional


def add_log(message: str, log_type: str = "info") -> None:
    """
    Add a log entry to the current request's log list.
    
    Args:
        message: The log message
        log_type: Type of log - "info", "success", "warning", "error"
    """
    try:
        # Try to import g from flask
        from flask import g
        
        # Ensure g.logs exists
        if not hasattr(g, 'logs'):
            g.logs = []
        
        # Create log entry
        log_entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],  # HH:MM:SS.mmm
            "message": message,
            "type": log_type
        }
        
        g.logs.append(log_entry)
        
        # Also print to console for debugging
        emoji_map = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌"
        }
        emoji = emoji_map.get(log_type, "📝")
        print(f"{emoji} [{log_entry['timestamp']}] {message}")
        
    except (ImportError, RuntimeError):
        # Flask context not available (e.g., during testing or standalone execution)
        # Just print to console
        print(f"[STANDALONE LOG] {message}")


def get_logs() -> list:
    """
    Retrieve all logs from the current request.
    
    Returns:
        List of log entries, or empty list if no logs exist
    """
    try:
        from flask import g
        return getattr(g, 'logs', [])
    except (ImportError, RuntimeError):
        return []


def clear_logs() -> None:
    """
    Clear all logs from the current request.
    """
    try:
        from flask import g
        g.logs = []
    except (ImportError, RuntimeError):
        pass
