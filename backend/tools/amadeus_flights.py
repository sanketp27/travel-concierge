"""Amadeus API integration for flight search and booking.

This module provides the service class and agent-callable tool functions
for interacting with the Amadeus Flight Search APIs.
"""

import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import requests

# --- Service Class for Amadeus API Interaction ---

class AmadeusFlightsService:
    """
    Service class to handle all interactions with the Amadeus Flight APIs.
    Manages API credentials, authentication (OAuth2), and request execution.
    """

    def __init__(self):
        """Initializes the Amadeus service, loading credentials from environment variables."""
        self.api_key = os.getenv("AMADEUS_CLIENT_ID")
        self.api_secret = os.getenv("AMADEUS_CLIENT_SECRET")
        self.base_url = "https://test.api.amadeus.com"  # Use production URL for live data
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None

        if not self.api_key or not self.api_secret:
            raise ValueError("AMADEUS_API_KEY and AMADEUS_API_SECRET environment variables must be set.")

    def _get_access_token(self) -> str:
        """
        Retrieves a new OAuth2 access token from Amadeus if the current one is
        missing or expired. Caches the token for reuse.
        """
        if self.access_token and self.token_expires_at and datetime.now() < self.token_expires_at:
            return self.access_token

        url = f"{self.base_url}/v1/security/oauth2/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.api_secret
        }

        try:
            response = requests.post(url, headers=headers, data=data, timeout=10)
            response.raise_for_status()
            token_data = response.json()

            self.access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 1799)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)

            return self.access_token
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get Amadeus access token: {e}")

    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Makes an authenticated GET request to a specified Amadeus API endpoint.
        """
        token = self._get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        full_url = f"{self.base_url}{endpoint}"

        try:
            response = requests.get(full_url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            error_details = e.response.text if e.response else "No response from server"
            raise Exception(f"Amadeus API request to {endpoint} failed: {e}. Details: {error_details}")

    def _make_post_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Makes an authenticated POST request to a specified Amadeus API endpoint.
        """
        token = self._get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/vnd.amadeus+json"
        }
        full_url = f"{self.base_url}{endpoint}"

        try:
            response = requests.post(full_url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            error_details = e.response.text if e.response else "No response from server"
            raise Exception(f"Amadeus API POST request to {endpoint} failed: {e}. Details: {error_details}")

    def search_flights(self,
                      origin: str,
                      destination: str,
                      departure_date: str,
                      return_date: Optional[str] = None,
                      adults: int = 1,
                      children: int = 0,
                      infants: int = 0,
                      travel_class: str = "ECONOMY",
                      max_price: Optional[int] = None,
                      currency_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Search for flights using Amadeus API.
       
        Args:
            origin: IATA code for origin airport (e.g., 'NYC', 'LAX')
            destination: IATA code for destination airport (e.g., 'PAR', 'LHR')
            departure_date: Departure date in YYYY-MM-DD format
            return_date: Return date in YYYY-MM-DD format (optional for one-way)
            adults: Number of adult passengers
            children: Number of child passengers
            infants: Number of infant passengers
            travel_class: Travel class (ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST)
            max_price: Maximum price filter (in the specified currency)
            currency_code: Currency code (e.g., 'INR', 'USD', 'EUR'). Defaults to INR, falls back to USD.
       
        Returns:
            Dictionary containing flight search results
        """
        if not currency_code:
            currency_code = os.getenv("AMADEUS_CURRENCY", "INR")
       
        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "adults": adults,
            "children": children,
            "infants": infants,
            "travelClass": travel_class,
            "currencyCode": currency_code.upper(),
            "max": 10
        }

        if return_date:
            params["returnDate"] = return_date

        if max_price:
            params["maxPrice"] = max_price

        return self._make_request("/v2/shopping/flight-offers", params)
   
    def get_flight_offers(self,
                         origin: str,
                         destination: str,
                         departure_date: str,
                         return_date: Optional[str] = None,
                         adults: int = 1,
                         currency_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Get flight offers with pricing and booking details.
       
        Args:
            origin: IATA code for origin airport
            destination: IATA code for destination airport
            departure_date: Departure date in YYYY-MM-DD format
            return_date: Return date in YYYY-MM-DD format (optional)
            adults: Number of adult passengers
            currency_code: Currency code (e.g., 'INR', 'USD', 'EUR'). Defaults to INR, falls back to USD.
        """
        if not currency_code:
            currency_code = os.getenv("AMADEUS_CURRENCY", "INR")
       
        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "adults": adults,
            "currencyCode": currency_code.upper()
        }
       
        if return_date:
            params["returnDate"] = return_date
       
        return self._make_request("/v2/shopping/flight-offers", params)
   
    def get_airport_city_code(self, query: str) -> str:
        """
        Get IATA code for a city name.
        """
        params = {"keyword": query, "subType": "AIRPORT,CITY"}
        result = self._make_request("/v1/reference-data/locations", params)

        if result and result.get("data"):
            return result["data"][0]["iataCode"]
        return query

    def check_flight_availability(self,
                                  origin: str,
                                  destination: str,
                                  departure_date: str,
                                  departure_time: Optional[str] = None,
                                  travelers: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Check flight seat availability using Amadeus Flight Availabilities API.
        
        Args:
            origin: IATA code for origin airport
            destination: IATA code for destination airport
            departure_date: Departure date in YYYY-MM-DD format
            departure_time: Departure time in HH:MM:SS format (optional)
            travelers: List of traveler dictionaries with 'id' and 'travelerType' 
                      (e.g., [{"id": "1", "travelerType": "ADULT"}])
        
        Returns:
            Dictionary containing flight availability information
        """
        if travelers is None:
            travelers = [{"id": "1", "travelerType": "ADULT"}]
        
        departure_datetime = {"date": departure_date}
        if departure_time:
            departure_datetime["time"] = departure_time
        
        payload = {
            "originDestinations": [
                {
                    "id": "1",
                    "originLocationCode": origin,
                    "destinationLocationCode": destination,
                    "departureDateTime": departure_datetime
                }
            ],
            "travelers": travelers,
            "sources": ["GDS"]
        }
        
        return self._make_post_request("/v1/shopping/availability/flight-availabilities", payload)

    def get_nearest_airports(self,
                           latitude: float,
                           longitude: float,
                           radius: int = 500,
                           page_limit: int = 10,
                           page_offset: int = 0,
                           sort: str = "relevance") -> Dict[str, Any]:
        """
        Get nearest airports to a given geographic location.
        
        Args:
            latitude: Latitude of the location (e.g., 51.57285)
            longitude: Longitude of the location (e.g., -0.44161)
            radius: Search radius in kilometers (0-500, default 500)
            page_limit: Maximum items per page (default 10)
            page_offset: Start index for pagination (default 0)
            sort: Sort order - 'relevance', 'distance', 'analytics.flights.score', 
                  or 'analytics.travelers.score' (default 'relevance')
        
        Returns:
            Dictionary containing list of nearby airports
        """
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "radius": radius,
            "page[limit]": page_limit,
            "page[offset]": page_offset,
            "sort": sort
        }
        
        return self._make_request("/v1/reference-data/locations/airports", params)

    def confirm_flight_pricing(self,
                              flight_offers: List[Dict[str, Any]],
                              include_options: Optional[List[str]] = None,
                              force_class: bool = False) -> Dict[str, Any]:
        """
        Confirm pricing for given flight offers.
        
        Args:
            flight_offers: List of flight offer dictionaries to confirm pricing for
            include_options: Optional list of additional info to include:
                           ['credit-card-fees', 'bags', 'other-services', 'detailed-fare-rules']
            force_class: Force usage of booking class for pricing (default False)
        
        Returns:
            Dictionary containing confirmed pricing information
        """
        payload = {
            "data": {
                "type": "flight-offers-pricing",
                "flightOffers": flight_offers
            }
        }
        
        params = {}
        if include_options:
            params["include"] = ",".join(include_options)
        if force_class:
            params["forceClass"] = "true"
        
        endpoint = "/v1/shopping/flight-offers/pricing"
        if params:
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            endpoint = f"{endpoint}?{query_string}"
        
        return self._make_post_request(endpoint, payload)


# --- Agent-Callable Tools ---

# Initialize the service as a singleton
amadeus_flights_service = AmadeusFlightsService()

def search_flights_tool(**kwargs) -> Dict[str, Any]:
    """
    Unified flight search tool accepting dynamic parameters.
    
    Request Body:
    {
        "origin": str (required) - Origin airport/city code
        "destination": str (required) - Destination airport/city code
        "departure_date": str (required) - YYYY-MM-DD
        "return_date": str (optional) - YYYY-MM-DD
        "adults": int (optional, default=1)
        "children": int (optional, default=0)
        "infants": int (optional, default=0)
        "travel_class": str (optional, default="ECONOMY")
        "max_price": int (optional)
        "currency_code": str (optional, default="INR")
    }
    """
    try:
        # Extract parameters with defaults
        origin = kwargs.get('origin')
        destination = kwargs.get('destination')
        departure_date = kwargs.get('departure_date')
        
        if not all([origin, destination, departure_date]):
            return {"error": "Missing required parameters: origin, destination, departure_date"}
        
        return_date = kwargs.get('return_date')
        adults = kwargs.get('adults', 1)
        children = kwargs.get('children', 0)
        infants = kwargs.get('infants', 0)
        
        # Ensure travel_class is uppercase and valid
        travel_class = kwargs.get('travel_class', 'ECONOMY')
        if isinstance(travel_class, str):
            travel_class = travel_class.upper()
        # Valid travel classes: ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST
        valid_classes = ['ECONOMY', 'PREMIUM_ECONOMY', 'BUSINESS', 'FIRST']
        if travel_class not in valid_classes:
            travel_class = 'ECONOMY'
        
        # Validate max_price - must be numeric, not a string
        max_price = kwargs.get('max_price')
        if max_price is not None:
            # If max_price is a string like "economy", remove it
            if isinstance(max_price, str):
                try:
                    # Try to convert to number
                    max_price = float(max_price)
                except (ValueError, TypeError):
                    # If it's not a number (e.g., "economy"), set to None
                    max_price = None
            elif not isinstance(max_price, (int, float)):
                max_price = None
        
        currency_code = kwargs.get('currency_code', 'INR')
        
        # Get airport/city codes
        origin_code = amadeus_flights_service.get_airport_city_code(origin) if len(origin) > 3 else origin
        destination_code = amadeus_flights_service.get_airport_city_code(destination) if len(destination) > 3 else destination

        results = amadeus_flights_service.search_flights(
            origin=origin_code,
            destination=destination_code,
            departure_date=departure_date,
            return_date=return_date,
            adults=adults,
            children=children,
            infants=infants,
            travel_class=travel_class,
            max_price=max_price,
            currency_code=currency_code
        )
        
        return results
        
    except Exception as e:
        return {"error": f"Flight search failed: {str(e)}"}


def get_flight_offers_tool(**kwargs) -> Dict[str, Any]:
    """
    Get flight offers tool.
    
    Request Body:
    {
        "origin": str (required)
        "destination": str (required)
        "departure_date": str (required) - YYYY-MM-DD
        "return_date": str (optional) - YYYY-MM-DD
        "adults": int (optional, default=1)
        "currency_code": str (optional, default="INR")
    }
    """
    try:
        origin = kwargs.get('origin')
        destination = kwargs.get('destination')
        departure_date = kwargs.get('departure_date')
        
        if not all([origin, destination, departure_date]):
            return {"error": "Missing required parameters"}
        
        
        
        results = amadeus_flights_service.search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=kwargs.get('return_date'),
            adults=kwargs.get('adults', 1),
            currency_code=kwargs.get('currency_code', 'INR')
        )
        
        return results
        
    except Exception as e:
        return {"error": f"Get flight offers failed: {str(e)}"}


def check_flight_availability_tool(**kwargs) -> Dict[str, Any]:
    """
    Check flight availability tool.
    
    Request Body:
    {
        "origin": str (required)
        "destination": str (required)
        "departure_date": str (required) - YYYY-MM-DD
        "departure_time": str (optional) - HH:MM:SS
        "num_adults": int (optional, default=1)
        "num_children": int (optional, default=0)
        "num_infants": int (optional, default=0)
    }
    """
    try:
        origin = kwargs.get('origin')
        destination = kwargs.get('destination')
        departure_date = kwargs.get('departure_date')
        
        if not all([origin, destination, departure_date]):
            return {"error": "Missing required parameters"}
        
        
        
        # Build travelers list
        travelers = []
        traveler_id = 1
        
        for _ in range(kwargs.get('num_adults', 1)):
            travelers.append({"id": str(traveler_id), "travelerType": "ADULT"})
            traveler_id += 1
        
        for _ in range(kwargs.get('num_children', 0)):
            travelers.append({"id": str(traveler_id), "travelerType": "CHILD"})
            traveler_id += 1
        
        for _ in range(kwargs.get('num_infants', 0)):
            travelers.append({"id": str(traveler_id), "travelerType": "HELD_INFANT"})
            traveler_id += 1
        
        results = amadeus_flights_service.check_flight_availability(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            departure_time=kwargs.get('departure_time'),
            travelers=travelers
        )
        
        return results
        
    except Exception as e:
        return {"error": f"Check flight availability failed: {str(e)}"}


def get_nearest_airports_tool(**kwargs) -> Dict[str, Any]:
    """
    Get nearest airports tool.
    
    Request Body:
    {
        "location": str (required) - Location name
        "radius": int (optional, default=500) - 0-500 km
        "max_results": int (optional, default=10)
        "sort_by": str (optional, default="relevance")
    }
    """
    try:
        location = kwargs.get('location')
        
        if not location:
            return {"error": "Missing required parameter: location"}
        
        from tools.map_tools import get_geocode
        
        
        geo_result = get_geocode(location)
        lat = geo_result['geometry']['location']['lat']
        lng = geo_result['geometry']['location']['lng']
        
        results = amadeus_flights_service.get_nearest_airports(
            latitude=lat,
            longitude=lng,
            radius=kwargs.get('radius', 500),
            page_limit=kwargs.get('max_results', 10),
            sort=kwargs.get('sort_by', 'relevance')
        )
        
        return results
        
    except Exception as e:
        return {"error": f"Get nearest airports failed: {str(e)}"}


def confirm_flight_pricing_tool(**kwargs) -> Dict[str, Any]:
    """
    Confirm flight pricing tool.
    
    Request Body:
    {
        "flight_offer": dict (required) - Complete flight offer object from search_flights_tool response
        "include_credit_card_fees": bool (optional, default=False)
        "include_bags": bool (optional, default=False)
        "include_other_services": bool (optional, default=False)
        "include_detailed_fare_rules": bool (optional, default=False)
        "force_booking_class": bool (optional, default=False)
    }
    
    Example flight_offer object:
    {
        "type": "flight-offer",
        "id": "1",
        "source": "GDS",
        "instantTicketingRequired": false,
        "nonHomogeneous": false,
        "oneWay": false,
        "lastTicketingDate": "2025-12-19",
        "numberOfBookableSeats": 9,
        "itineraries": [...],
        "price": {
            "currency": "INR",
            "total": "14875.00",
            "base": "12000.00"
        },
        "pricingOptions": {...},
        "validatingAirlineCodes": ["AI"],
        "travelerPricings": [...]
    }
    """
    try:
        # Validate that this is NOT a hotel request
        hotel_params = ['hotel_id', 'check_in_date', 'check_out_date', 'city']
        provided_params = set(kwargs.keys())
        hotel_params_found = [p for p in hotel_params if p in provided_params]
        
        if hotel_params_found:
            return {
                "error": f"Invalid parameters for confirm_flight_pricing_tool. Found hotel parameters: {hotel_params_found}. "
                        f"This tool requires 'flight_offer' (a complete flight offer object from search_flights_tool). "
                        f"For hotels, use 'get_hotel_details_tool' instead."
            }
        
        flight_offer = kwargs.get('flight_offer')
        
        if not flight_offer:
            return {
                "error": "Missing required parameter: flight_offer",
                "details": "This tool requires a complete flight offer object (dict) from search_flights_tool response.",
                "example": {
                    "flight_offer": {
                        "type": "flight-offer",
                        "id": "1",
                        "itineraries": [...],
                        "price": {"currency": "INR", "total": "14875.00"}
                    }
                }
            }
        
        # Validate flight_offer structure
        if not isinstance(flight_offer, dict):
            return {
                "error": "Invalid flight_offer type. Expected dict, got {}".format(type(flight_offer).__name__)
            }
        
        # Check for required flight offer fields
        required_fields = ['type', 'id', 'itineraries', 'price']
        missing_fields = [f for f in required_fields if f not in flight_offer]
        if missing_fields:
            return {
                "error": f"Invalid flight_offer structure. Missing required fields: {missing_fields}",
                "details": "flight_offer must be a complete object from search_flights_tool response"
            }
        
        # Build include options
        include_options = []
        if kwargs.get('include_credit_card_fees', False):
            include_options.append("credit-card-fees")
        if kwargs.get('include_bags', False):
            include_options.append("bags")
        if kwargs.get('include_other_services', False):
            include_options.append("other-services")
        if kwargs.get('include_detailed_fare_rules', False):
            include_options.append("detailed-fare-rules")
        
        results = amadeus_flights_service.confirm_flight_pricing(
            flight_offers=[flight_offer],
            include_options=include_options if include_options else None,
            force_class=kwargs.get('force_booking_class', False)
        )
        
        return results
        
    except Exception as e:
        return {"error": f"Confirm flight pricing failed: {str(e)}"}