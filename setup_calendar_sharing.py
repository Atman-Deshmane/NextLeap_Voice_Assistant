"""
Script to share the service account calendar with your personal Google account.
This allows you to see events created by the service account in your personal calendar.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.google_calendar import _get_calendar_service

def share_calendar_with_email(email_address: str, role: str = "reader"):
    """
    Share the service account's primary calendar with an email address.
    
    Args:
        email_address: Email to share calendar with
        role: Access role - "owner", "writer", or "reader" (default)
    """
    try:
        service = _get_calendar_service()
        
        # Create ACL rule
        rule = {
            'scope': {
                'type': 'user',
                'value': email_address,
            },
            'role': role  # owner, writer, reader
        }
        
        created_rule = service.acl().insert(calendarId='primary', body=rule).execute()
        
        print(f"✅ Calendar shared successfully with {email_address}")
        print(f"   Access level: {role}")
        print(f"   Rule ID: {created_rule['id']}")
        print("\n📧 Check your email! You should receive a calendar sharing invitation.")
        print("   Accept the invitation to see events in your Google Calendar.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error sharing calendar: {e}")
        return False


def main():
    print("=" * 60)
    print("Google Calendar Sharing Setup")
    print("=" * 60)
    
    # Get email from user
    email = input("\n📧 Enter your Google email address: ").strip()
    
    if not email or '@' not in email:
        print("❌ Invalid email address")
        return
    
    print(f"\n🔄 Sharing calendar with {email}...")
    
    if share_calendar_with_email(email, role="owner"):
        print("\n" + "=" * 60)
        print("Setup Complete! ✅")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Check your email inbox")
        print("2. Accept the calendar sharing invitation")
        print("3. All events created by the scheduler will now appear in your calendar!")
    else:
        print("\n❌ Failed to share calendar. Check your service account credentials.")


if __name__ == "__main__":
    main()
