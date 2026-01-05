"""
Test script for Google Calendar integration.
Creates a test event to verify the service account authentication and API access.
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path to import services
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.google_calendar import create_event, test_connection

def main():
    print("=" * 60)
    print("Google Calendar Integration Test")
    print("=" * 60)
    
    # Test 1: Connection test
    print("\n[Test 1] Testing connection to Google Calendar API...")
    if test_connection():
        print("✅ Connection test PASSED")
    else:
        print("❌ Connection test FAILED")
        return
    
    # Test 2: Create a test event
    print("\n[Test 2] Creating test event for today at 6pm...")
    
    # Today at 6pm IST
    today = datetime.now()
    event_start = today.replace(hour=18, minute=0, second=0, microsecond=0)
    event_end = event_start + timedelta(hours=1)
    
    start_iso = event_start.strftime("%Y-%m-%dT%H:%M:%S+05:30")
    end_iso = event_end.strftime("%Y-%m-%dT%H:%M:%S+05:30")
    
    print(f"   Event time: {event_start.strftime('%Y-%m-%d %H:%M')} - {event_end.strftime('%H:%M')} IST")
    
    event_link = create_event(
        summary="Test Event - Working Session",
        start_time_iso=start_iso,
        end_time_iso=end_iso,
        description="This is a test event created by the HDFC Advisor Scheduler to verify Google Calendar integration."
    )
    
    if event_link:
        print(f"✅ Event created successfully!")
        print(f"   Link: {event_link}")
    else:
        print("❌ Event creation FAILED")
        print("\n" + "=" * 60)
        print("Possible issues:")
        print("1. GOOGLE_SERVICE_ACCOUNT_JSON not set in .env")
        print("2. Service account JSON is malformed")
        print("3. Service account doesn't have calendar access")
        print("4. Calendar API not enabled for the project")
        print("=" * 60)
        return
    
    print("\n" + "=" * 60)
    print("All tests PASSED! ✅")
    print("=" * 60)

if __name__ == "__main__":
    main()
