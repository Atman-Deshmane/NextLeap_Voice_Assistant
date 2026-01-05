"""
Database Manager for the Advisor Scheduler.
Provides functions to safely manipulate the store.json file.
"""

import json
import os
import random
import string
from typing import List, Dict, Optional, Any

# Import logger for debug transparency
from services import logger

# Path to store.json (relative to project root)
STORE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "store.json")


def _load_store() -> Dict:
    """Load the store.json file."""
    with open(STORE_PATH, 'r') as f:
        return json.load(f)


def _save_store(data: Dict) -> None:
    """Save data to store.json file."""
    with open(STORE_PATH, 'w') as f:
        json.dump(data, f, indent=2)


def _generate_booking_code() -> str:
    """
    Generate a random 5-character booking code.
    Format: NL-XXXX (where X is alphanumeric)
    Example: NL-A742, NL-X99Z
    """
    chars = string.ascii_uppercase + string.digits
    code = ''.join(random.choices(chars, k=4))
    return f"NL-{code}"


def check_availability(date_str: str) -> List[str]:
    """
    Check available time slots for a given date.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        
    Returns:
        List of available time slots (e.g., ["14:00", "15:00"])
        Empty list if no slots available or date not found
    """
    logger.add_log(f"🔍 Checking availability for {date_str}", "info")
    
    store = _load_store()
    
    if date_str not in store["slots"]:
        logger.add_log(f"⚠️ No slots found for {date_str}", "warning")
        return []
    
    available_times = []
    for time_slot, slot_data in store["slots"][date_str].items():
        if slot_data["status"] == "available":
            available_times.append(time_slot)
    
    logger.add_log(f"✅ Found {len(available_times)} available slot(s)", "success")
    return sorted(available_times)


def book_slot(
    date_str: str, 
    time_str: str, 
    topic: str, 
    user_alias: str = "Anonymous"
) -> Dict[str, Any]:
    """
    Book an available slot.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        time_str: Time in HH:MM format (e.g., "14:00")
        topic: One of [KYC/Onboarding, SIP/Mandates, Statements/Tax Docs, Withdrawals, Account Changes]
        user_alias: Optional name/alias (default: "Anonymous")
        
    Returns:
        Dict with status and booking code on success, or error message on failure
        Success: {"status": "success", "code": "NL-X99Z", "date": "2026-01-07", "time": "14:00"}
        Failure: {"status": "error", "message": "Slot not available"}
    """
    logger.add_log(f"📝 Attempting to book slot: {date_str} at {time_str} for {topic}", "info")
    
    store = _load_store()
    
    # Check if date exists
    if date_str not in store["slots"]:
        logger.add_log(f"❌ Date {date_str} not available", "error")
        return {
            "status": "error",
            "message": f"No slots available for date {date_str}"
        }
    
    # Check if time slot exists
    if time_str not in store["slots"][date_str]:
        logger.add_log(f"❌ Invalid time slot {time_str}", "error")
        return {
            "status": "error",
            "message": f"Invalid time slot {time_str}. Available slots are 14:00 and 15:00."
        }
    
    # Check if slot is available
    slot = store["slots"][date_str][time_str]
    if slot["status"] != "available":
        logger.add_log(f"❌ Slot already booked", "error")
        return {
            "status": "error",
            "message": f"Slot at {time_str} on {date_str} is already booked"
        }
    
    # Generate booking code and update slot (tentative booking)
    booking_code = _generate_booking_code()
    logger.add_log(f"🎫 Generated booking code: {booking_code}", "success")
    
    store["slots"][date_str][time_str] = {
        "status": "booked",
        "booking_id": booking_code,
        "topic": topic,
        "user_alias": user_alias
    }
    
    _save_store(store)
    logger.add_log(f"💾 Saved booking to local database", "success")
    
    # Create Google Calendar event (synchronous)
    calendar_success = False
    event_link = None
    
    try:
        logger.add_log(f"📅 Connecting to Google Calendar Service Account...", "info")
        from services.google_calendar import create_event
        from datetime import datetime, timedelta
        
        # Parse the date and time
        booking_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        
        # Create ISO timestamps for 1-hour appointment
        start_time_iso = booking_datetime.strftime("%Y-%m-%dT%H:%M:%S+05:30")
        end_time_iso = (booking_datetime + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S+05:30")
        
        # Create event
        event_link = create_event(
            summary=f"HDFC Mutual Funds - {topic} Consultation",
            start_time_iso=start_time_iso,
            end_time_iso=end_time_iso,
            description=f"""Appointment Details:
- Topic: {topic}
- Booking Code: {booking_code}
- User: {user_alias}

This is an automated booking from HDFC Mutual Funds Advisor Scheduler.
"""
        )
        
        calendar_success = event_link is not None
        
        if calendar_success:
            logger.add_log(f"✅ Google Calendar event created successfully", "success")
        else:
            logger.add_log(f"⚠️ Calendar API returned no event link", "warning")
        
    except Exception as e:
        logger.add_log(f"❌ Google Calendar error: {str(e)}", "error")
        calendar_success = False
    
    # Prepare response
    response = {
        "status": "success",
        "code": booking_code,
        "date": date_str,
        "time": time_str,
        "topic": topic,
        "user_alias": user_alias
    }
    
    # Add confirmation message based on calendar result
    if calendar_success:
        response["message"] = "Booking Confirmed! Event added to your Google Calendar."
        if event_link:
            response["calendar_link"] = event_link
        logger.add_log(f"🎉 Booking completed successfully with calendar integration", "success")
    else:
        response["message"] = "Booking saved locally. Note: Calendar event could not be created automatically."
        logger.add_log(f"⚠️ Booking completed but calendar integration failed", "warning")
    
    return response


def cancel_slot(booking_code: str) -> Dict[str, Any]:
    """
    Cancel a booking by its booking code.
    Searches entire store for the code and resets the slot to available.
    
    Args:
        booking_code: The booking code (e.g., "NL-X99Z")
        
    Returns:
        Dict with status and details
        Success: {"status": "success", "message": "Booking NL-X99Z cancelled", "date": "2026-01-07", "time": "14:00"}
        Failure: {"status": "error", "message": "Booking code not found"}
    """
    store = _load_store()
    
    # Search for the booking code across all dates and times
    for date_str, times in store["slots"].items():
        for time_str, slot_data in times.items():
            if slot_data.get("booking_id") == booking_code:
                # Found the booking - reset to available
                store["slots"][date_str][time_str] = {
                    "status": "available",
                    "booking_id": None,
                    "topic": None,
                    "user_alias": None
                }
                
                _save_store(store)
                
                # Trigger n8n webhook for cancellation
                try:
                    from services.n8n_client import trigger_mcp_action
                    trigger_mcp_action("cancel", {
                        "code": booking_code,
                        "date": date_str,
                        "time": time_str
                    })
                except ImportError:
                    pass
                except Exception as e:
                    print(f"Warning: Failed to trigger n8n webhook: {e}")
                
                return {
                    "status": "success",
                    "message": f"Booking {booking_code} cancelled successfully",
                    "date": date_str,
                    "time": time_str
                }
    
    return {
        "status": "error",
        "message": f"Booking code {booking_code} not found"
    }


def add_to_waitlist(
    date_str: str, 
    topic: str, 
    user_alias: str = "Anonymous"
) -> Dict[str, Any]:
    """
    Add a user to the waitlist for a specific date.
    
    Args:
        date_str: Preferred date in YYYY-MM-DD format
        topic: One of [KYC/Onboarding, SIP/Mandates, Statements/Tax Docs, Withdrawals, Account Changes]
        user_alias: Optional name/alias (default: "Anonymous")
        
    Returns:
        Dict with status and waitlist position
    """
    logger.add_log(f"📋 Slot full. Adding {user_alias} to waitlist for {date_str}", "info")
    
    store = _load_store()
    
    waitlist_entry = {
        "date": date_str,
        "topic": topic,
        "user_alias": user_alias,
        "waitlist_id": _generate_booking_code()  # Generate unique ID for waitlist
    }
    
    store["waitlist"].append(waitlist_entry)
    _save_store(store)
    
    logger.add_log(f"✅ Added to waitlist (Position: {len(store['waitlist'])})", "success")
    
    # Trigger n8n webhook for waitlist
    try:
        from services.n8n_client import trigger_mcp_action
        trigger_mcp_action("waitlist", waitlist_entry)
    except ImportError:
        pass
    except Exception as e:
        print(f"Warning: Failed to trigger n8n webhook: {e}")
    
    return {
        "status": "success",
        "message": f"Added to waitlist for {date_str}",
        "waitlist_id": waitlist_entry["waitlist_id"],
        "position": len(store["waitlist"])
    }


def find_booking_by_name_and_time(
    user_alias: str, 
    time_str: Optional[str] = None,
    date_str: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Find bookings by user alias and optionally time/date.
    Useful for reschedule/cancel when user provides name instead of booking code.
    
    Args:
        user_alias: The name/alias used during booking
        time_str: Optional time filter (HH:MM format)
        date_str: Optional date filter (YYYY-MM-DD format)
        
    Returns:
        List of matching bookings with their details
    """
    store = _load_store()
    matches = []
    
    for date, times in store["slots"].items():
        if date_str and date != date_str:
            continue
            
        for time, slot_data in times.items():
            if time_str and time != time_str:
                continue
                
            if (slot_data.get("user_alias", "").lower() == user_alias.lower() and 
                slot_data.get("status") == "booked"):
                matches.append({
                    "booking_id": slot_data["booking_id"],
                    "date": date,
                    "time": time,
                    "topic": slot_data["topic"],
                    "user_alias": slot_data["user_alias"]
                })
    
    return matches


def get_all_available_dates() -> List[str]:
    """
    Get all dates that have at least one available slot.
    
    Returns:
        List of date strings in YYYY-MM-DD format
    """
    store = _load_store()
    available_dates = []
    
    for date_str, times in store["slots"].items():
        for slot_data in times.values():
            if slot_data["status"] == "available":
                available_dates.append(date_str)
                break  # Only need to find one available slot per date
    
    return sorted(available_dates)
