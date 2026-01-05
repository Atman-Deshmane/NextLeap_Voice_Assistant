"""
LLM Engine for the Advisor Scheduler.
Handles Gemini AI integration with function calling capabilities.
"""

import os
import json
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types

# Import database functions for tool execution
from services.db_manager import (
    check_availability,
    book_slot,
    cancel_booking,
    add_to_waitlist,
    find_booking_by_name_and_time,
    get_all_available_dates
)

from datetime import datetime

# Import history manager for session logging
from services import history_manager

# System prompt with all rules
def get_system_prompt():
    current_date = datetime.now().strftime("%B %d, %Y")
    return f"""You are the HDFC Mutual Funds Advisor Scheduler. Today is {current_date}.

Your role is to help users schedule appointments with financial advisors. You have DIRECT ACCESS to the User's Google Calendar - all bookings are REAL and will be automatically added to their calendar.

You must strictly follow these rules:

## RULE 1: NO INVESTMENT ADVICE
- You are NOT authorized to give investment advice under any circumstances.
- If a user asks about investments, mutual funds performance, or financial advice, politely refuse and redirect them to booking an appointment with an advisor.
- Example response: "I'm not authorized to provide investment advice. However, I can help you schedule an appointment with one of our expert advisors who can assist you."

## RULE 2: MANDATORY TOPIC CONFIRMATION
- Before proceeding with booking or checking availability, you MUST confirm the user's topic.
- Valid topics are: [KYC/Onboarding, SIP/Mandates, Statements/Tax Docs, Withdrawals, Account Changes]
- If the user's intent is unclear, ASK a clarifying question BEFORE asking for date preferences.
- Do not guess or assume the topic - always confirm explicitly.

## RULE 3: USE TOOLS FOR ALL DATA OPERATIONS
- ALWAYS use the provided functions (tools) to check availability, book slots, or cancel bookings.
- Do NOT hallucinate or make up slot availability - only report what the tools return.
- When checking availability, call check_availability with the exact date.

## RULE 4: DATE HANDLING
- When a user gives a relative date (e.g., "next Friday", "tomorrow"), calculate the absolute date (YYYY-MM-DD format) based on today being {current_date}.
- Today is {datetime.now().strftime("%A, %B %d, %Y")}.
- NOTE: Appointments are ONLY available starting from January 7, 2026 to January 21, 2026.
- If a user asks for a date before Jan 7th, politely inform them that bookings open from Jan 7th.
- Available slots are only on weekdays (Monday-Friday), 2 PM (14:00) and 3 PM (15:00) IST.

## RULE 5: BOOKING FLOW
1. Greet with disclaimer: "Welcome to HDFC Mutual Funds Advisor Scheduler. Please note this service is for informational purposes only and does not constitute investment advice."
2. Confirm the topic before proceeding.
3. Ask for date/time preference.
4. Use check_availability to find available slots.
5. Offer up to 2 available slots.
6. When booking, generate a booking code.
7. Ask for an optional name (default: "Anonymous").
8. Provide a mock "Secure Link" for them to complete their details: https://hdfc.mf/secure/<booking_code>

## RULE 6: STRICT NO PII POLICY
- Do NOT ask for or accept: phone numbers, email addresses, PAN numbers, account numbers, or any personal identification.
- If a user volunteers PII, acknowledge but do not store it. Redirect to the secure link.

## RULE 7: RESCHEDULE/CANCEL FLOW
- User can provide their Booking Code (e.g., "NL-X99Z") OR Name+Time to modify booking.
- Use cancel_slot to cancel, then book_slot to rebook if rescheduling.

## RULE 8: WAITLIST
- If no slots match the user's preference, offer to add them to the waitlist using add_to_waitlist.

Be professional, helpful, and concise. Always maintain a friendly but formal tone appropriate for financial services.
"""



class LLMEngine:
    """
    LLM Engine that manages conversation with Gemini and handles function calling.
    """
    
    def __init__(self):
        """Initialize the Gemini client and model."""
        api_key = os.getenv("GEMINI_API_KEY_NextLeap")
        if not api_key:
            raise ValueError("GEMINI_API_KEY_NextLeap environment variable not set")
        
        self.client = genai.Client(api_key=api_key)
        self.model_id = "gemini-3-flash-preview"
        
        # Create function declarations using proper Schema objects
        check_availability_func = types.FunctionDeclaration(
            name="check_availability",
            description="Check available appointment slots for a specific date. Returns a list of available times (e.g., ['14:00', '15:00']).",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "date_str": types.Schema(
                        type=types.Type.STRING,
                        description="The date to check in YYYY-MM-DD format (e.g., '2026-01-07')"
                    )
                },
                required=["date_str"]
            )
        )
        
        book_slot_func = types.FunctionDeclaration(
            name="book_slot",
            description="Book an available appointment slot. Returns booking confirmation with a unique booking code.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "date_str": types.Schema(
                        type=types.Type.STRING,
                        description="The date to book in YYYY-MM-DD format"
                    ),
                    "time_str": types.Schema(
                        type=types.Type.STRING,
                        description="The time slot to book in HH:MM format (either '14:00' or '15:00')"
                    ),
                    "topic": types.Schema(
                        type=types.Type.STRING,
                        description="The appointment topic. Must be one of: KYC/Onboarding, SIP/Mandates, Statements/Tax Docs, Withdrawals, Account Changes"
                    ),
                    "user_alias": types.Schema(
                        type=types.Type.STRING,
                        description="Optional name or alias for the booking. Default is 'Anonymous'"
                    )
                },
                required=["date_str", "time_str", "topic"]
            )
        )
        
        cancel_slot_func = types.FunctionDeclaration(
            name="cancel_slot",
            description="Cancel an existing booking using the booking code. Resets the slot to available.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "booking_code": types.Schema(
                        type=types.Type.STRING,
                        description="The booking code (e.g., 'NL-X99Z') provided during booking"
                    )
                },
                required=["booking_code"]
            )
        )
        
        add_to_waitlist_func = types.FunctionDeclaration(
            name="add_to_waitlist",
            description="Add a user to the waitlist for a specific date when no slots are available.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "date_str": types.Schema(
                        type=types.Type.STRING,
                        description="The preferred date in YYYY-MM-DD format"
                    ),
                    "topic": types.Schema(
                        type=types.Type.STRING,
                        description="The appointment topic"
                    ),
                    "user_alias": types.Schema(
                        type=types.Type.STRING,
                        description="Optional name or alias. Default is 'Anonymous'"
                    )
                },
                required=["date_str", "topic"]
            )
        )
        
        get_all_available_dates_func = types.FunctionDeclaration(
            name="get_all_available_dates",
            description="Get a list of all dates that have at least one available slot.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={},
                required=[]
            )
        )
        
        find_booking_func = types.FunctionDeclaration(
            name="find_booking_by_name_and_time",
            description="Find existing bookings by user name/alias and optionally filter by date or time. Useful for reschedule/cancel when user doesn't have booking code.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "user_alias": types.Schema(
                        type=types.Type.STRING,
                        description="The name or alias used during booking"
                    ),
                    "time_str": types.Schema(
                        type=types.Type.STRING,
                        description="Optional time filter in HH:MM format"
                    ),
                    "date_str": types.Schema(
                        type=types.Type.STRING,
                        description="Optional date filter in YYYY-MM-DD format"
                    )
                },
                required=["user_alias"]
            )
        )
        
        # Create tool with all function declarations
        self.tools = [types.Tool(function_declarations=[
            check_availability_func,
            book_slot_func,
            cancel_slot_func,
            add_to_waitlist_func,
            get_all_available_dates_func,
            find_booking_func
        ])]
        
        # Conversation history
        self.conversation_history: List[types.Content] = []
        
        # Session tracking for history logging
        self.current_session_id: Optional[str] = None
    
    def _execute_function(self, function_name: str, function_args: Dict[str, Any]) -> Any:
        """
        Execute a function based on its name and arguments.
        
        Args:
            function_name: Name of the function to execute
            function_args: Arguments to pass to the function
            
        Returns:
            Result of the function execution
        """
        function_map = {
            "check_availability": check_availability,
            "book_slot": book_slot,
            "cancel_slot": cancel_booking,
            "add_to_waitlist": add_to_waitlist,
            "get_all_available_dates": get_all_available_dates,
            "find_booking_by_name_and_time": find_booking_by_name_and_time
        }
        
        if function_name not in function_map:
            return {"error": f"Unknown function: {function_name}"}
        
        try:
            result = function_map[function_name](**function_args)
            return result
        except Exception as e:
            return {"error": str(e)}
    
    def chat(self, user_message: str) -> Dict[str, Any]:
        """
        Process a user message and return the assistant's response.
        Handles function calling loop automatically.
        
        Args:
            user_message: The user's message
            
        Returns:
            Dict containing 'text' and optional 'ui_hint'
        """
        # Add user message to history
        self.conversation_history.append(
            types.Content(
                role="user",
                parts=[types.Part(text=user_message)]
            )
        )
        
        # Start session if not already started
        if self.current_session_id is None:
            self.current_session_id = history_manager.start_session()
        
        # Generate config with system instruction and tools
        config = types.GenerateContentConfig(
            system_instruction=get_system_prompt(),
            tools=self.tools
        )
        
        # Maximum iterations for function calling loop
        max_iterations = 10
        iteration = 0
        ui_hint = None
        
        while iteration < max_iterations:
            iteration += 1
            
            # Call the model
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=self.conversation_history,
                config=config
            )
            
            # Check if we have a response
            if not response.candidates or not response.candidates[0].content.parts:
                return {"text": "I apologize, but I couldn't generate a response. Please try again.", "ui_hint": None}
            
            response_parts = response.candidates[0].content.parts
            
            # Check for function calls
            function_calls = [part for part in response_parts if part.function_call]
            
            if function_calls:
                # Add assistant's function call to history
                self.conversation_history.append(
                    types.Content(
                        role="model",
                        parts=response_parts
                    )
                )
                
                # Execute each function and collect results
                function_responses = []
                for part in function_calls:
                    fc = part.function_call
                    result = self._execute_function(fc.name, dict(fc.args))
                    
                    # Capture UI Hints from Tool Calls
                    if fc.name == "check_availability":
                        ui_hint = {
                            "type": "calendar_widget", 
                            "data": {
                                "date": fc.args.get("date_str"), 
                                "slots": result if isinstance(result, list) else []
                            }
                        }
                    elif fc.name == "book_slot" and isinstance(result, dict) and result.get("status") == "success":
                        ui_hint = {"type": "booking_card", "data": result}
                    elif fc.name == "find_booking_by_name_and_time" and isinstance(result, dict) and result.get("status") == "success":
                         # Only show manage card if we found exactly one booking or a list of bookings
                         ui_hint = {"type": "manage_card", "data": result}

                    function_responses.append(
                        types.Part(
                            function_response=types.FunctionResponse(
                                name=fc.name,
                                response={"result": result}
                            )
                        )
                    )
                
                # Add function results to history
                self.conversation_history.append(
                    types.Content(
                        role="user",
                        parts=function_responses
                    )
                )
            else:
                # No function calls - we have the final response
                text_parts = [part.text for part in response_parts if part.text]
                final_response = " ".join(text_parts) if text_parts else "I'm here to help you schedule an appointment."
                
                # Detect Topic Selector Intent if no other hint is set
                if not ui_hint and ("topic" in final_response.lower() and "?" in final_response):
                    ui_hint = {"type": "topic_selector"}

                # Add assistant response to history
                self.conversation_history.append(
                    types.Content(
                        role="model",
                        parts=[types.Part(text=final_response)]
                    )
                )
                
                # Log the conversation turn to disk
                if self.current_session_id:
                    history_manager.log_turn(
                        self.current_session_id, 
                        user_message, 
                        final_response
                    )
                
                return {"text": final_response, "ui_hint": ui_hint}
        
        return {"text": "I apologize, but I'm having trouble processing your request. Please try again.", "ui_hint": None}
    
    def reset_conversation(self):
        """Reset the conversation history and start a new session."""
        self.conversation_history = []
        self.current_session_id = None  # Will create new session on next chat
    
    def get_greeting(self) -> str:
        """Get the initial greeting message."""
        return self.chat("Hello")


# Singleton instance
_engine_instance: Optional[LLMEngine] = None


def get_engine() -> LLMEngine:
    """Get or create the LLM engine singleton."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = LLMEngine()
    return _engine_instance


def reset_engine():
    """Reset the engine instance (useful for starting new conversations)."""
    global _engine_instance
    if _engine_instance:
        _engine_instance.reset_conversation()
