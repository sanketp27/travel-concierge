"""
Unified Travel API Structure with Request/Response Schemas
This module defines the structure for all travel-related functions
that can be triggered via LLM with standardized request bodies.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# ============================================================================
# FLIGHTS API STRUCTURE
# ============================================================================

FLIGHTS_API = {
    "search_flights": {
        "function_name": "search_flights_tool",
        "description": "Search for available flights between two locations",
        "request_schema": {
            "origin": {"type": "string", "required": True, "example": "NYC"},
            "destination": {"type": "string", "required": True, "example": "LAX"},
            "departure_date": {"type": "string", "required": True, "format": "YYYY-MM-DD", "example": "2025-12-01"},
            "return_date": {"type": "string", "required": False, "format": "YYYY-MM-DD", "example": "2025-12-10"},
            "adults": {"type": "integer", "required": False, "default": 1, "example": 2},
            "children": {"type": "integer", "required": False, "default": 0, "example": 0},
            "infants": {"type": "integer", "required": False, "default": 0, "example": 0},
            "travel_class": {"type": "string", "required": False, "default": "ECONOMY", 
                           "enum": ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"]},
            "max_price": {"type": "integer", "required": False, "example": 50000},
            "currency_code": {"type": "string", "required": False, "default": "INR", "example": "INR"}
        }
    },
    "get_flight_offers": {
        "function_name": "get_flight_offers_tool",
        "description": "Get detailed flight offers with pricing information",
        "request_schema": {
            "origin": {"type": "string", "required": True, "example": "BOM"},
            "destination": {"type": "string", "required": True, "example": "DEL"},
            "departure_date": {"type": "string", "required": True, "format": "YYYY-MM-DD"},
            "return_date": {"type": "string", "required": False, "format": "YYYY-MM-DD"},
            "adults": {"type": "integer", "required": False, "default": 1},
            "currency_code": {"type": "string", "required": False, "default": "INR"}
        }
    },
    "check_flight_availability": {
        "function_name": "check_flight_availability_tool",
        "description": "Check seat availability for specific flights",
        "request_schema": {
            "origin": {"type": "string", "required": True, "example": "BOS"},
            "destination": {"type": "string", "required": True, "example": "MAD"},
            "departure_date": {"type": "string", "required": True, "format": "YYYY-MM-DD"},
            "departure_time": {"type": "string", "required": False, "format": "HH:MM:SS", "example": "21:15:00"},
            "num_adults": {"type": "integer", "required": False, "default": 1},
            "num_children": {"type": "integer", "required": False, "default": 0},
            "num_infants": {"type": "integer", "required": False, "default": 0}
        }
    },
    "get_nearest_airports": {
        "function_name": "get_nearest_airports_tool",
        "description": "Find airports near a geographic location",
        "request_schema": {
            "location": {"type": "string", "required": True, "example": "Mumbai, India"},
            "radius": {"type": "integer", "required": False, "default": 500, "min": 0, "max": 500},
            "max_results": {"type": "integer", "required": False, "default": 10},
            "sort_by": {"type": "string", "required": False, "default": "relevance",
                       "enum": ["relevance", "distance", "analytics.flights.score", "analytics.travelers.score"]}
        }
    },
    "confirm_flight_pricing": {
        "function_name": "confirm_flight_pricing_tool",
        "description": "Confirm and validate pricing for a specific flight offer",
        "request_schema": {
            "flight_offer_id": {"type": "string", "required": True, "example": "1"},
            "include_credit_card_fees": {"type": "boolean", "required": False, "default": False},
            "include_bags": {"type": "boolean", "required": False, "default": False},
            "include_other_services": {"type": "boolean", "required": False, "default": False},
            "include_detailed_fare_rules": {"type": "boolean", "required": False, "default": False},
            "force_booking_class": {"type": "boolean", "required": False, "default": False}
        }
    }
}

# ============================================================================
# HOTELS API STRUCTURE
# ============================================================================

HOTELS_API = {
    "search_hotels": {
        "function_name": "search_hotels_tool",
        "description": "Search for available hotels in a city",
        "request_schema": {
            "city": {"type": "string", "required": True, "example": "Mumbai"},
            "check_in_date": {"type": "string", "required": True, "format": "YYYY-MM-DD", "example": "2025-12-01"},
            "check_out_date": {"type": "string", "required": True, "format": "YYYY-MM-DD", "example": "2025-12-05"},
            "adults": {"type": "integer", "required": False, "default": 1, "example": 2},
            "rooms": {"type": "integer", "required": False, "default": 1, "example": 1}
        }
    },
    "get_hotel_details": {
        "function_name": "get_hotel_details_tool",
        "description": "Get detailed information about a specific hotel",
        "request_schema": {
            "hotel_id": {"type": "string", "required": True, "example": "HTMUMBAI123"}
        }
    }
}

# ============================================================================
# TRAINS API STRUCTURE
# ============================================================================

TRAINS_API = {
    "get_live_train_status": {
        "function_name": "get_live_train_status_tool",
        "description": "Get live running status of a train",
        "request_schema": {
            "train_number": {"type": "string", "required": True, "example": "12952"},
            "date": {"type": "string", "required": True, "format": "YYYY-MM-DD or 'today'/'tomorrow'", "example": "today"}
        }
    },
    "search_trains": {
        "function_name": "search_trains_tool",
        "description": "Search trains between two stations",
        "request_schema": {
            "from_station": {"type": "string", "required": True, "example": "NDLS"},
            "to_station": {"type": "string", "required": True, "example": "BCT"},
            "date": {"type": "string", "required": True, "format": "YYYY-MM-DD or 'today'/'tomorrow'", "example": "2025-12-01"}
        }
    },
    "get_trains_by_station": {
        "function_name": "get_trains_by_station_tool",
        "description": "Get all trains passing through a station",
        "request_schema": {
            "station_code": {"type": "string", "required": True, "example": "NDLS"}
        }
    },
    "check_seat_availability": {
        "function_name": "check_seat_availability_tool",
        "description": "Check seat availability for a train",
        "request_schema": {
            "train_number": {"type": "string", "required": True, "example": "19038"},
            "from_station": {"type": "string", "required": True, "example": "ST"},
            "to_station": {"type": "string", "required": True, "example": "BVI"},
            "class_type": {"type": "string", "required": True, "example": "2A",
                          "enum": ["1A", "2A", "3A", "SL", "2S", "CC"]},
            "quota": {"type": "string", "required": True, "example": "GN",
                     "enum": ["GN", "TQ", "PT", "LD"]},
            "date": {"type": "string", "required": True, "format": "YYYY-MM-DD"}
        }
    },
    "get_train_schedule": {
        "function_name": "get_train_schedule_tool",
        "description": "Get complete schedule/route for a train",
        "request_schema": {
            "train_number": {"type": "string", "required": True, "example": "12936"}
        }
    },
    "get_train_fare": {
        "function_name": "get_train_fare_tool",
        "description": "Get fare information for a train",
        "request_schema": {
            "train_number": {"type": "string", "required": True, "example": "19038"},
            "from_station": {"type": "string", "required": True, "example": "ST"},
            "to_station": {"type": "string", "required": True, "example": "BVI"}
        }
    }
}

# ============================================================================
# MAPS API STRUCTURE
# ============================================================================

MAPS_API = {
    "find_places": {
        "function_name": "find_places_tool",
        "description": "Search for places based on text query",
        "request_schema": {
            "query": {"type": "string", "required": True, "example": "museums in Paris"}
        }
    },
    "get_place_details": {
        "function_name": "get_place_details_tool",
        "description": "Get detailed information about a place",
        "request_schema": {
            "place_id": {"type": "string", "required": True, "example": "ChIJD7fiBh9u5kcRYJSMaMOCCwQ"}
        }
    },
    "get_route": {
        "function_name": "get_route_tool",
        "description": "Calculate route between two locations",
        "request_schema": {
            "origin": {"type": "string", "required": True, "example": "Eiffel Tower"},
            "destination": {"type": "string", "required": True, "example": "Louvre Museum"},
            "travel_mode": {"type": "string", "required": True, "example": "WALK",
                           "enum": ["DRIVE", "WALK", "TRANSIT", "BICYCLE"]}
        }
    },
    "optimize_day_trip": {
        "function_name": "optimize_day_trip_tool",
        "description": "Optimize the order of visiting multiple stops",
        "request_schema": {
            "start_location": {"type": "string", "required": True, "example": "My Hotel, Paris"},
            "end_location": {"type": "string", "required": True, "example": "My Hotel, Paris"},
            "stops": {"type": "array", "items": {"type": "string"}, "required": True,
                     "example": ["Eiffel Tower", "Louvre Museum", "Notre Dame"]}
        }
    },
    "get_weather_forecast": {
        "function_name": "get_weather_forecast_tool",
        "description": "Get weather forecast for a location",
        "request_schema": {
            "location": {"type": "string", "required": True, "example": "Paris, France"}
        }
    },
    "get_air_quality": {
        "function_name": "get_air_quality_tool",
        "description": "Get air quality information for a location",
        "request_schema": {
            "location": {"type": "string", "required": True, "example": "Delhi, India"}
        }
    }
}

# ============================================================================
# UNIFIED API STRUCTURE
# ============================================================================

UNIFIED_TRAVEL_API = {
    "flights": FLIGHTS_API,
    "hotels": HOTELS_API,
    "trains": TRAINS_API,
    "maps": MAPS_API
}


# ============================================================================
# EXAMPLE REQUEST BODIES
# ============================================================================

EXAMPLE_REQUESTS = {
    "flights": {
        "search_flights": {
            "origin": "BOM",
            "destination": "DEL",
            "departure_date": "2025-12-15",
            "return_date": "2025-12-20",
            "adults": 2,
            "travel_class": "ECONOMY",
            "currency_code": "INR"
        },
        "check_flight_availability": {
            "origin": "BOM",
            "destination": "DEL",
            "departure_date": "2025-12-15",
            "num_adults": 2
        }
    },
    "hotels": {
        "search_hotels": {
            "city": "Mumbai",
            "check_in_date": "2025-12-15",
            "check_out_date": "2025-12-20",
            "adults": 2,
            "rooms": 1
        }
    },
    "trains": {
        "search_trains": {
            "from_station": "NDLS",
            "to_station": "BCT",
            "date": "2025-12-15"
        },
        "check_seat_availability": {
            "train_number": "12952",
            "from_station": "NDLS",
            "to_station": "BCT",
            "class_type": "2A",
            "quota": "GN",
            "date": "2025-12-15"
        }
    },
    "maps": {
        "find_places": {
            "query": "restaurants in Mumbai"
        },
        "get_route": {
            "origin": "Gateway of India, Mumbai",
            "destination": "Marine Drive, Mumbai",
            "travel_mode": "WALK"
        }
    }
}
