#!/usr/bin/env python3
"""
Initialization script to populate store.json with appointment slots.
Generates weekday slots (14:00 and 15:00 IST) from Jan 7-21, 2026.
"""

import json
from datetime import datetime, timedelta
import os

def generate_store_data():
    """Generate the store.json structure with available slots."""
    
    # Date range: Jan 7, 2026 to Jan 21, 2026
    start_date = datetime(2026, 1, 7)
    end_date = datetime(2026, 1, 21)
    
    # Available time slots (IST)
    time_slots = ["14:00", "15:00"]
    
    store = {
        "slots": {},
        "waitlist": []
    }
    
    current_date = start_date
    while current_date <= end_date:
        # Only include weekdays (Monday=0 to Friday=4)
        if current_date.weekday() < 5:
            date_str = current_date.strftime("%Y-%m-%d")
            store["slots"][date_str] = {}
            
            for time_slot in time_slots:
                store["slots"][date_str][time_slot] = {
                    "status": "available",
                    "booking_id": None,
                    "topic": None,
                    "user_alias": None
                }
        
        current_date += timedelta(days=1)
    
    return store


def main():
    """Main function to create and save store.json."""
    store_path = os.path.join(os.path.dirname(__file__), "store.json")
    
    store_data = generate_store_data()
    
    with open(store_path, 'w') as f:
        json.dump(store_data, f, indent=2)
    
    # Print summary
    dates = list(store_data["slots"].keys())
    print(f"✅ store.json created successfully!")
    print(f"📅 Date range: {dates[0]} to {dates[-1]}")
    print(f"📊 Total dates: {len(dates)} weekdays")
    print(f"⏰ Slots per day: 14:00 (2 PM) and 15:00 (3 PM) IST")
    print(f"📍 Total slots: {len(dates) * 2}")
    
    # List all dates
    print("\n📆 Dates included:")
    for date in dates:
        day_name = datetime.strptime(date, "%Y-%m-%d").strftime("%A")
        print(f"   - {date} ({day_name})")


if __name__ == "__main__":
    main()
