"""
n8n Webhook Client for triggering external actions.
Sends POST requests to n8n webhook for calendar/email integrations.
"""

import requests
import json


def trigger_mcp_action(action_type: str, data: dict) -> bool:
    """
    Send a POST request to the n8n webhook to trigger external actions.
    
    Args:
        action_type: Type of action - "book", "waitlist", or "cancel"
        data: Payload containing booking details
            - For "book": {code, date, time, topic, user_alias}
            - For "waitlist": {date, topic, user_alias, waitlist_id}
            - For "cancel": {code, date, time}
    
    Returns:
        True if n8n webhook returns 200 OK, False otherwise
    """
    # Hardcoded URL for testing (will move to .env after verification)
    webhook_url = "https://n8n.srv1060037.hstgr.cloud/mcp/f37787c1-8c17-4810-8a86-9c71c6e69cf9"
    
    # Prepare payload
    payload = {
        "action": action_type,
        "payload": data
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        print(f"🔌 N8N REQUEST: {action_type} | URL: {webhook_url}")
        print(f"📦 N8N PAYLOAD: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            webhook_url,
            json=payload,
            headers=headers,
            timeout=10
        )
        
        print(f"🔌 N8N STATUS: {response.status_code} | RESPONSE: {response.text}")
        
        # Return True only if status is 200
        if response.status_code == 200:
            print("✅ N8N Webhook successful!")
            return True
        else:
            print(f"⚠️ N8N Webhook failed with status {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ N8N Webhook request timed out")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ N8N Webhook error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error in N8N webhook: {str(e)}")
        return False
