"""Google Maps Platform API integration for a Travel Itinerary Agent.

This module provides the service class and agent-callable tool functions
for interacting with the Google Maps Platform APIs, including:
- Places API (New)
- Routes API
- Route Optimization API
- Geocoding API (as a helper)
- Weather API
- Air Quality API
"""

import os
import requests
from typing import Dict, List, Any, Optional

# --- Service Class for Google Maps Platform API Interaction ---

class GoogleMapsService:
    """
    Service class to handle all interactions with the Google Maps Platform APIs.
    Manages API key authentication and executes REST API requests.
    """

    def __init__(self):
        """Initializes the Google Maps service, loading the API key."""
        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_MAPS_API_KEY environment variable must be set.")

    def _get_default_headers(self) -> Dict[str, str]:
        """Returns the default headers for new v1/v2 Google APIs."""
        return {
            "X-Goog-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }

    def _make_post_request(self, url: str, json_data: Dict, field_mask: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Makes an authenticated POST request to a specified Google API endpoint.

        Args:
            url: The full API endpoint URL.
            json_data: The JSON payload for the POST request.
            field_mask: A list of fields to return (e.g., "places.displayName").

        Returns:
            The JSON response from the API.
        """
        headers = self._get_default_headers()
        if field_mask:
            headers["X-Goog-Fieldmask"] = ",".join(field_mask)

        try:
            response = requests.post(url, json=json_data, headers=headers, timeout=20)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.RequestException as e:
            error_details = e.response.text if e.response else "No response from server"
            raise Exception(f"Google API POST request to {url} failed: {e}. Details: {error_details}")

    def _make_get_request(self, url: str, params: Dict = None, field_mask: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Makes an authenticated GET request to a specified Google API endpoint.
        Used for APIs like Place Details (New) and the older Geocoding API.
        """
        headers = self._get_default_headers()
        if field_mask:
            headers["X-Goog-Fieldmask"] = ",".join(field_mask)
        
        # The new v1 GET APIs use headers, but the old ones (Geocoding) use a 'key' param.
        # This logic handles both by adding the key to params only if it's not a v1/v2 header-based request.
        if "X-Goog-Api-Key" not in headers:
            if params is None:
                params = {}
            params["key"] = self.api_key

        try:
            response = requests.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            error_details = e.response.text if e.response else "No response from server"
            raise Exception(f"Google API GET request to {url} failed: {e}. Details: {error_details}")

    # --- Helper API Methods ---
    
    def geocode(self, address: str) -> Dict[str, Any]:
        """
        Converts a string address into geographic coordinates (lat/lng) and a place_id.
        Uses the standard Geocoding API.
        """
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": address, "key": self.api_key}
        # This uses a simple GET request, not the header-based _make_get_request
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "OK" and data.get("results"):
                return data['results'][0]
            else:
                raise Exception(f"Geocoding returned status: {data.get('status')}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Geocoding request for '{address}' failed: {e}")

    # --- Places API (New) Methods ---

    def text_search(self, query: str) -> Dict[str, Any]:
        """Searches for a set of places based on a text query (e.g., "museums in Paris")."""
        url = "https://places.googleapis.com/v1/places:searchText"
        json_data = {"textQuery": query}
        # Define the fields you want back. This controls cost and data.
        field_mask = [
            "places.id", 
            "places.displayName", 
            "places.formattedAddress", 
            "places.types"
        ]
        return self._make_post_request(url, json_data, field_mask)

    def get_place_details(self, place_id: str) -> Dict[str, Any]:
        """Gets detailed information about a specific place."""
        url = f"https://places.googleapis.com/v1/places/{place_id}"
        # Define the fields you want. This is a good set for a travel agent.
        field_mask = [
            "id", 
            "displayName", 
            "formattedAddress", 
            "photos", 
            "rating",
            "userRatingCount",
            "websiteUri",
            "regularOpeningHours",
            "priceLevel"
        ]
        return self._make_get_request(url, field_mask=field_mask)

    # --- Routes API Methods ---

    def compute_route(self, origin: Dict[str, str], destination: Dict[str, str], travel_mode: str) -> Dict[str, Any]:
        """Calculates a route between two points."""
        url = "https://routes.googleapis.com/directions/v2:computeRoutes"
        json_data = {
            "origin": {"location": origin},
            "destination": {"location": destination},
            "travelMode": travel_mode.upper(),
            "routingPreference": "TRAFFIC_AWARE",
            "computeAlternativeRoutes": False,
        }
        # Define the fields you want in the response
        field_mask = [
            "routes.duration",
            "routes.distanceMeters",
            "routes.polyline.encodedPolyline",
            "routes.summary"
        ]
        return self._make_post_request(url, json_data, field_mask)

    # --- Route Optimization API Methods ---

    def optimize_tour(self, start_place_id: str, end_place_id: str, stop_place_ids: List[str]) -> Dict[str, Any]:
        """
        Calculates the most efficient order to visit a series of stops.
        
        This creates a simple single-vehicle model for a day trip.
        """
        url = "https://routeoptimization.googleapis.com/v1:optimizeTours"
        
        # Build the 'shipments' (stops to visit)
        shipments = [{
            "pickups": [{
                "arrivalLocation": {"placeId": place_id},
                "duration": "600s"  # Assumes a 10-minute visit at each stop
            }]
        } for place_id in stop_place_ids]

        # Build the 'vehicle'
        vehicle = {
            "model": {
                "startLocation": {"placeId": start_place_id},
                "endLocation": {"placeId": end_place_id},
                "shipments": shipments
            }
        }
        
        json_data = {
            "parent": f"projects/{os.getenv('GOOGLE_PROJECT_ID')}", # Route Optimization needs Project ID
            "model": vehicle['model']
        }
        
        return self._make_post_request(url, json_data)

    # --- Environment API Methods ---
    
    def get_forecast(self, lat: float, lng: float) -> Dict[str, Any]:
        """Gets the daily weather forecast for a location."""
        # Use correct endpoint: weather:lookup (not forecast:lookup)
        url = "https://weather.googleapis.com/v1/weather:lookup"
        # Weather API uses POST request with location in body
        json_data = {
            "location": {
                "latitude": lat,
                "longitude": lng
            },
            "extraComputation": ["FORECAST"]
        }
        return self._make_post_request(url, json_data)

    def get_air_quality(self, lat: float, lng: float) -> Dict[str, Any]:
        """Gets the current air quality conditions for a location."""
        url = "https://airquality.googleapis.com/v1/currentConditions:lookup"
        json_data = {
            "location": {
                "latitude": lat,
                "longitude": lng
            }
        }
        return self._make_post_request(url, json_data)


# --- Agent-Callable Tools ---

# Singleton service instance
google_maps_service = None


def _get_service() -> GoogleMapsService:
    """Get or create the Google Maps service instance."""
    global google_maps_service
    if google_maps_service is None:
        google_maps_service = GoogleMapsService()
    return google_maps_service


def get_geocode(location: str):
    """
    Gets the daily weather forecast for a location.

    Args:
        location: The address or name of the location (e.g., "Paris, France").

    Returns:
        A dictionary with the weather forecast or an error.
    """
    try:
        service = _get_service()
        # Weather API needs coordinates. We must geocode first.
        geo_result = service.geocode(location)
        return geo_result
    except Exception as e:
        return {"error": f"Get weather forecast failed: {str(e)}"}


def find_places_tool(**kwargs) -> Dict[str, Any]:
    """
    Find places tool.
    
    Request Body:
    {
        "query": str (required) - Search query
    }
    """
    try:
        query = kwargs.get('query')
        
        if not query:
            return {"error": "Missing required parameter: query"}
        
        service = _get_service()
        
        results = service.text_search(query)
        
        return results
        
    except Exception as e:
        return {"error": f"Find places failed: {str(e)}"}


def get_place_details_tool(**kwargs) -> Dict[str, Any]:
    """
    Get place details tool.
    
    Request Body:
    {
        "place_id": str (required)
    }
    """
    try:
        place_id = kwargs.get('place_id')
        
        if not place_id:
            return {"error": "Missing required parameter: place_id"}
    
        service = _get_service()
        
        results = service.get_place_details(place_id)
        
        return results
        
    except Exception as e:
        return {"error": f"Get place details failed: {str(e)}"}


def get_route_tool(**kwargs) -> Dict[str, Any]:
    """
    Get route tool.
    
    Request Body:
    {
        "origin": str (required)
        "destination": str (required)
        "travel_mode": str (required) - "DRIVE", "WALK", "TRANSIT", "BICYCLE"
    }
    """
    try:
        origin = kwargs.get('origin')
        destination = kwargs.get('destination')
        travel_mode = kwargs.get('travel_mode')
        
        if not all([origin, destination, travel_mode]):
            return {"error": "Missing required parameters"}
        
        service = _get_service()
        
        origin_payload = {"address": origin}
        dest_payload = {"address": destination}
        
        results = service.compute_route(origin_payload, dest_payload, travel_mode)
        
        return results
        
    except Exception as e:
        return {"error": f"Get route failed: {str(e)}"}


def optimize_day_trip_tool(**kwargs) -> Dict[str, Any]:
    """
    Optimize day trip tool.
    
    Request Body:
    {
        "start_location": str (required)
        "end_location": str (required)
        "stops": list[str] (required)
    }
    """
    try:
        start_location = kwargs.get('start_location')
        end_location = kwargs.get('end_location')
        stops = kwargs.get('stops')
        
        if not all([start_location, end_location, stops]):
            return {"error": "Missing required parameters"}
        
        if not isinstance(stops, list):
            return {"error": "stops must be a list"}

        service = _get_service()
        
        start_place_id = service.geocode(start_location)['place_id']
        end_place_id = service.geocode(end_location)['place_id']
        stop_place_ids = [service.geocode(s)['place_id'] for s in stops]
        
        results = service.optimize_tour(start_place_id, end_place_id, stop_place_ids)
        
        return results
        
    except Exception as e:
        return {"error": f"Optimize day trip failed: {str(e)}"}


def get_weather_forecast_tool(**kwargs) -> Dict[str, Any]:
    """
    Get weather forecast tool.
    
    Request Body:
    {
        "location": str (required)
    }
    """
    try:
        location = kwargs.get('location')
        
        if not location:
            return {"error": "Missing required parameter: location"}
        
        service = _get_service()
        
        geo_result = service.geocode(location)
        lat = geo_result['geometry']['location']['lat']
        lng = geo_result['geometry']['location']['lng']
        
        results = service.get_forecast(lat, lng)
        
        return results
        
    except Exception as e:
        return {"error": f"Get weather forecast failed: {str(e)}"}


def get_air_quality_tool(**kwargs) -> Dict[str, Any]:
    """
    Get air quality tool.
    
    Request Body:
    {
        "location": str (required)
    }
    """
    try:
        location = kwargs.get('location')
        
        if not location:
            return {"error": "Missing required parameter: location"}
        
        service = _get_service()
        
        geo_result = service.geocode(location)
        lat = geo_result['geometry']['location']['lat']
        lng = geo_result['geometry']['location']['lng']
        
        results = service.get_air_quality(lat, lng)
        
        return results
        
    except Exception as e:
        return {"error": f"Get air quality failed: {str(e)}"}