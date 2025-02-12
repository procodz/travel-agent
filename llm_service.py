# llm_service.py

import requests
from typing import Dict, Any

class LLMService:
    def __init__(self, api_url: str = "http://localhost:11434/api/generate"):
        self.api_url = api_url

    def get_recommendation(self, query: str, context: Dict[str, Any]) -> str:
        """Get recommendations from the LLM with user preferences"""
        prompt = f"""
        You are a smart travel guide assistant. The user's query is "{query}".

        Context:
        - Source Station: {context['source']}
        - Destination Station: {context['destination']}
        - Available Trains: {context['available_trains']}
        - Seat Availability: {context.get('seat_availability', 'Not available')}
        - Travel Date: {context['travel_date']}
        - User Priority: {context.get('priority', 'Not specified')}
        - Alternative Routes Available: {context.get('alternative_routes', [])}
        - Nearby Station Options: {context.get('nearby_stations', [])}

        Provide a detailed response including:
        1. Best direct routes if available
        2. Alternative routes with transfers
        3. Options from nearby stations if relevant
        4. Recommendations based on user's priority (speed/cost/comfort)
        5. Seat availability and booking suggestions
        """
        
        try:
            response = requests.post(
                self.api_url,
                headers={"Content-Type": "application/json"},
                json={
                    "model": "qwen2.5:3b",
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            return response.json().get("response", "Unable to generate recommendation.")
        except requests.RequestException as e:
            return f"Error generating recommendation: {str(e)}"

    def process_natural_language(self, query: str) -> Dict[str, Any]:
        """Process natural language query to extract travel details"""
        try:
            response = requests.post(
                self.api_url,
                headers={"Content-Type": "application/json"},
                json={
                    "model": "qwen2.5:3b",
                    "prompt": f"""
                    Extract travel details from this query: {query}
                    
                    Return only a JSON object with these fields:
                    - source: The departure station
                    - destination: The arrival station
                    - travel_date: The date of travel (if mentioned)
                    - preferences: Any mentioned preferences about speed, cost, or comfort
                    
                    If any field is not mentioned in the query, set it to null.
                    """,
                    "stream": False
                }
            )
            response.raise_for_status()
            llm_response = response.json().get("response", "")
            
            # You might need to add additional parsing logic here
            # depending on how your LLM formats its response
            
            return {
                "source": None,  # Extract from LLM response
                "destination": None,  # Extract from LLM response
                "travel_date": None,  # Extract from LLM response
                "preferences": {
                    "priority": "Speed",
                    "max_transfers": 2,
                    "include_overnight": True
                }
            }
        except requests.RequestException as e:
            return {
                "error": f"Error processing natural language query: {str(e)}"
            }