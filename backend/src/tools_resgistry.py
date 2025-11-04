"""
Unified Tool Registry for Travel Agent
Centralized tool execution with error handling.
"""

import traceback
from typing import Dict, Any, Callable

# ============================================================================ #
# Import all tool modules safely
# ============================================================================ #
try:
    from tools.amadeus_flights import *
    from tools.amadeus_hotels import *
    from tools.indian_railways import *
    from tools.map_tools import *
except ImportError as e:
    print(f"⚠️ Warning: Some tools failed to import: {e}")


# ============================================================================ #
# TOOL REGISTRY
# ============================================================================ #
TOOL_REGISTRY: Dict[str, Callable] = {
    # ✈️ Flights
    "search_flights_tool": globals().get("search_flights_tool"),
    "get_flight_offers_tool": globals().get("get_flight_offers_tool"),
    "check_flight_availability_tool": globals().get("check_flight_availability_tool"),
    "get_nearest_airports_tool": globals().get("get_nearest_airports_tool"),
    "confirm_flight_pricing_tool": globals().get("confirm_flight_pricing_tool"),

    # 🏨 Hotels
    "search_hotels_tool": globals().get("search_hotels_tool"),
    "get_hotel_details_tool": globals().get("get_hotel_details_tool"),

    # 🚆 Railways
    "get_live_train_status_tool": globals().get("get_live_train_status_tool"),
    "search_trains_tool": globals().get("search_trains_tool"),
    "get_trains_by_station_tool": globals().get("get_trains_by_station_tool"),
    "check_seat_availability_tool": globals().get("check_seat_availability_tool"),
    "get_train_schedule_tool": globals().get("get_train_schedule_tool"),
    "get_train_fare_tool": globals().get("get_train_fare_tool"),

    # 🗺️ Maps & Places
    "get_geocode": globals().get("get_geocode"),
    "find_places_tool": globals().get("find_places_tool"),
    "get_place_details_tool": globals().get("get_place_details_tool"),
    "get_route_tool": globals().get("get_route_tool"),
    "optimize_day_trip_tool": globals().get("optimize_day_trip_tool"),
    "get_weather_forecast_tool": globals().get("get_weather_forecast_tool"),
}


# ============================================================================ #
# TOOL EXECUTION WRAPPER
# ============================================================================ #
def execute_tool_by_name(function_name: str, parameters: Dict[str, Any]) -> Any:
    """Execute a registered tool by name with provided parameters."""
    print(f"\n🔧 [TOOL CALL] {function_name}")
    if parameters:
        preview = {
            k: (f"{v[:100]}... (truncated)" if isinstance(v, str) and len(v) > 100
                else f"{type(v).__name__} ({len(v)})" if isinstance(v, (dict, list))
                else v)
            for k, v in parameters.items()
        }
        print(f"   📋 Params: {preview}")

    try:
        func = TOOL_REGISTRY.get(function_name) or TOOL_REGISTRY.get(f"{function_name}_tool")
        if not func:
            available = [k for k, v in TOOL_REGISTRY.items() if v]
            return {"error": f"Function '{function_name}' not found.", "available_functions": available}

        if hasattr(func, "run"):
            result = func.run(**parameters)
        elif callable(func):
            result = func(**parameters)
        else:
            return {"error": f"Registered tool '{function_name}' is not callable."}

        print(f"   ✅ Completed: {function_name}")
        if isinstance(result, dict) and "error" in result:
            print(f"   ⚠️ Tool returned error: {result['error']}")
        return result

    except TypeError as e:
        return {
            "error": f"Invalid parameters for '{function_name}'",
            "details": str(e),
            "provided_params": list(parameters.keys()),
            "traceback": traceback.format_exc(),
        }
    except Exception as e:
        return {
            "error": f"Error executing '{function_name}'",
            "details": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc(),
        }
