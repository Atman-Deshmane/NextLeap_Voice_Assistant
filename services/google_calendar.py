"""
Google Calendar Integration for the Advisor Scheduler.
Uses Service Account authentication with credentials from environment variable.
"""

import os
import json
from typing import Optional
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Google Calendar scopes
SCOPES = ['https://www.googleapis.com/auth/calendar']


def _get_calendar_service():
    """
    Create and return an authenticated Google Calendar service.
    
    Returns:
        Google Calendar service object
        
    Raises:
        ValueError: If credentials are not configured
        Exception: If authentication fails
    """
    # Get service account JSON from environment variable
    service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    
    if not service_account_json:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON environment variable not set")
    
    try:
        # Parse the JSON string
        service_account_info = json.loads(service_account_json)
        
        # Create credentials from the service account info
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES
        )
        
        # Build and return the Calendar service
        service = build('calendar', 'v3', credentials=credentials)
        return service
        
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse GOOGLE_SERVICE_ACCOUNT_JSON: {e}")
    except Exception as e:
        raise Exception(f"Failed to authenticate with Google Calendar: {e}")


def create_event(
    summary: str,
    start_time_iso: str,
    end_time_iso: str,
    description: str,
    attendee_email: Optional[str] = None
) -> Optional[str]:
    """
    Create a Google Calendar event.
    
    Args:
        summary: Event title/summary
        start_time_iso: Start time in ISO 8601 format (e.g., '2026-01-07T14:00:00+05:30')
        end_time_iso: End time in ISO 8601 format
        description: Event description
        attendee_email: Optional email for attendee (default: None)
        
    Returns:
        HTML link to the created event, or None if creation failed
    """
    try:
        service = _get_calendar_service()
        
        # Prepare event data
        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_time_iso,
                'timeZone': 'Asia/Kolkata',  # IST
            },
            'end': {
                'dateTime': end_time_iso,
                'timeZone': 'Asia/Kolkata',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                    {'method': 'popup', 'minutes': 30},  # 30 minutes before
                ],
            },
        }
        
        # Add attendee if provided
        if attendee_email:
            event['attendees'] = [{'email': attendee_email}]
        
        # Create the event in the primary calendar
        created_event = service.events().insert(
            calendarId='primary',
            body=event,
            sendUpdates='all' if attendee_email else 'none'  # Send email if attendee provided
        ).execute()
        
        event_link = created_event.get('htmlLink')
        print(f"📅 Google Calendar event created: {event_link}")
        
        return event_link
        
    except ValueError as e:
        print(f"❌ Calendar Error: {e}")
        return None
    except HttpError as e:
        print(f"❌ Google Calendar API Error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected Calendar Error: {e}")
        return None


def test_connection() -> bool:
    """
    Test the Google Calendar connection.
    
    Returns:
        True if connection is successful, False otherwise
    """
    try:
        service = _get_calendar_service()
        # Try to list calendars to verify connection
        calendar_list = service.calendarList().list(maxResults=1).execute()
        print("✅ Google Calendar connection successful!")
        return True
    except Exception as e:
        print(f"❌ Google Calendar connection failed: {e}")
        return False
