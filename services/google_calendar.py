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
) -> Optional[dict]:
    """
    Create a Google Calendar event.
    
    Args:
        summary: Event title/summary
        start_time_iso: Start time in ISO 8601 format (e.g., '2026-01-07T14:00:00+05:30')
        end_time_iso: End time in ISO 8601 format
        description: Event description
        attendee_email: Optional email for attendee (default: None)
        
    Returns:
        Dict with 'event_id' and 'html_link', or None if creation failed
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
        # Try with attendee first, fall back to no attendee if service account limitation
        try:
            created_event = service.events().insert(
                calendarId='primary',
                body=event,
                sendUpdates='all' if attendee_email else 'none'
            ).execute()
        except HttpError as attendee_error:
            if 'forbiddenForServiceAccounts' in str(attendee_error):
                # Service account can't add attendees - remove and retry
                print(f"⚠️ Service account cannot add attendees, creating event without attendee")
                event.pop('attendees', None)
                created_event = service.events().insert(
                    calendarId='primary',
                    body=event,
                    sendUpdates='none'
                ).execute()
            else:
                raise attendee_error
        
        event_id = created_event.get('id')
        event_link = created_event.get('htmlLink')
        print(f"📅 Google Calendar event created: {event_link}")
        
        return {
            'event_id': event_id,
            'html_link': event_link
        }
        
    except ValueError as e:
        print(f"❌ Calendar Error: {e}")
        return None
    except HttpError as e:
        print(f"❌ Google Calendar API Error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected Calendar Error: {e}")
        return None


def delete_event(event_id: str) -> bool:
    """
    Delete a Google Calendar event by its ID.
    
    Args:
        event_id: The Google Calendar event ID
        
    Returns:
        True if deleted successfully, False otherwise
    """
    if not event_id:
        print("⚠️ No event ID provided for deletion")
        return False
    
    try:
        service = _get_calendar_service()
        
        # Delete the event
        service.events().delete(
            calendarId='primary',
            eventId=event_id
        ).execute()
        
        print(f"🗑️ Google Calendar event deleted: {event_id}")
        return True
        
    except HttpError as e:
        if e.resp.status == 404:
            print(f"⚠️ Calendar event not found (may already be deleted): {event_id}")
            return True  # Consider it successful if already gone
        print(f"❌ Google Calendar API Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Failed to delete calendar event: {e}")
        return False


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

