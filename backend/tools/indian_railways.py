"""Indian Railways integration for live train data via RapidAPI IRCTC."""

import os
from typing import Dict, Any
from datetime import datetime, timedelta
import requests


class IndianRailwaysService:
    """Service for interacting with RapidAPI IRCTC API.
    
    Configured specifically for RapidAPI IRCTC (irctc1.p.rapidapi.com).
    """

    def __init__(self):
        # Default to RapidAPI IRCTC if not set
        self.base_url = os.getenv("RAIL_API_BASE_URL", "https://irctc1.p.rapidapi.com")
        self.api_key = os.getenv("RAIL_API_KEY", "")
        self.api_host = os.getenv("RAIL_API_HOST", "irctc1.p.rapidapi.com")

        if not self.api_key:
            raise ValueError("RAIL_API_KEY must be set to use Indian Railways integration")

    def _headers(self) -> Dict[str, str]:
        """Return headers for RapidAPI IRCTC authentication."""
        return {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.api_host
        }

    def _get(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make authenticated GET request to RapidAPI IRCTC."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.get(url, headers=self._headers(), params=params or {}, timeout=20)
            
            # Check for subscription errors first
            if response.status_code == 403:
                try:
                    error_data = response.json()
                    if "not subscribed" in error_data.get("message", "").lower():
                        raise Exception(
                            "You are not subscribed to the IRCTC API on RapidAPI. "
                            "Please visit https://rapidapi.com/IRCTCAPI/api/irctc1 and subscribe to a plan."
                        )
                except (ValueError, KeyError):
                    pass
                
                raise Exception(
                    "403 Forbidden - Check your RapidAPI key. "
                    "Ensure RAIL_API_KEY is set correctly and you have an active subscription to IRCTC API. "
                    "Visit: https://rapidapi.com/IRCTCAPI/api/irctc1"
                )
            elif response.status_code == 429:
                raise Exception(
                    "429 Too Many Requests - Rate limit exceeded. "
                    "Please wait before making more requests."
                )
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            # Re-raise our custom exceptions
            if "not subscribed" in str(e).lower() or "403 Forbidden" in str(e) or "429 Too Many Requests" in str(e):
                raise
            raise Exception(f"Railways API request failed: {e}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Railways API request failed: {e}")

    def _date_to_start_day(self, date: str) -> int:
        """Convert date to startDay offset (1 = today, 2 = tomorrow, etc.).
        
        Args:
            date: Journey date in YYYY-MM-DD, YYYYMMDD, or relative ("today", "tomorrow")
        
        Returns:
            Integer day offset (1 for today, 2 for tomorrow, etc., max 30 days ahead)
        """
        try:
            today = datetime.now().date()
            
            # Handle relative dates
            date_lower = date.lower()
            if date_lower == "today":
                return 1
            elif date_lower == "tomorrow":
                return 2
            
            # Parse absolute dates
            if '-' in date:
                dt = datetime.strptime(date, "%Y-%m-%d").date()
            elif len(date) == 8 and date.isdigit():
                dt = datetime.strptime(date, "%Y%m%d").date()
            else:
                # Try DDMMYYYY format
                try:
                    dt = datetime.strptime(date, "%d%m%Y").date()
                except ValueError:
                    # Default to today if parsing fails
                    return 1
            
            # Calculate days difference
            delta = (dt - today).days + 1
            # Ensure it's between 1 (today) and 30 (reasonable limit for live status)
            return max(1, min(30, delta))
        except (ValueError, AttributeError):
            # Default to today if parsing fails
            return 1

    def get_live_train_status(self, train_number: str, date: str) -> Dict[str, Any]:
        """Fetch live train running status using RapidAPI IRCTC.

        Args:
            train_number: Numeric train number as string (e.g., "12952")
            date: Journey date in YYYY-MM-DD, YYYYMMDD format, or relative ("today", "tomorrow")
        """
        # RapidAPI IRCTC endpoint for live train status (actual endpoint from their docs)
        endpoint = os.getenv("RAIL_LIVE_STATUS_ENDPOINT", "/api/v1/liveTrainStatus")
        start_day = self._date_to_start_day(date)
        params = {
            "trainNo": train_number,
            "startDay": start_day
        }
        return self._get(endpoint, params)

    def _normalize_date(self, date: str) -> str:
        """Convert date to YYYY-MM-DD format expected by search API.
        
        Args:
            date: Journey date in various formats or relative ("today", "tomorrow")
        
        Returns:
            Date string in YYYY-MM-DD format
        """
        try:
            date_lower = date.lower()
            
            # Handle relative dates
            if date_lower == "today":
                return datetime.now().strftime("%Y-%m-%d")
            elif date_lower == "tomorrow":
                return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            
            # Parse absolute dates
            if '-' in date:
                # Already in YYYY-MM-DD or DD-MM-YYYY format
                if len(date.split('-')[0]) == 4:
                    # YYYY-MM-DD
                    dt = datetime.strptime(date, "%Y-%m-%d")
                else:
                    # DD-MM-YYYY
                    dt = datetime.strptime(date, "%d-%m-%Y")
                return dt.strftime("%Y-%m-%d")
            elif len(date) == 8 and date.isdigit():
                # YYYYMMDD format
                dt = datetime.strptime(date, "%Y%m%d")
                return dt.strftime("%Y-%m-%d")
            else:
                # Try DDMMYYYY format
                dt = datetime.strptime(date, "%d%m%Y")
                return dt.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            # Default to today if parsing fails
            return datetime.now().strftime("%Y-%m-%d")

    def search_trains_between_stations(self, from_station: str, to_station: str, date: str) -> Dict[str, Any]:
        """Search trains between two stations using RapidAPI IRCTC.

        Args:
            from_station: Source station code (e.g., "NDLS" for New Delhi)
            to_station: Destination station code (e.g., "BCT" for Mumbai Central)
            date: Journey date in YYYY-MM-DD, YYYYMMDD format, or relative ("today", "tomorrow")
        """
        # RapidAPI IRCTC endpoint for train search (actual endpoint from their docs)
        endpoint = os.getenv("RAIL_SEARCH_ENDPOINT", "/api/v1/searchTrain")
        formatted_date = self._normalize_date(date)
        params = {
            "fromStationCode": from_station.upper(),
            "toStationCode": to_station.upper(),
            "dateOfJourney": formatted_date
        }
        return self._get(endpoint, params)

    def get_trains_by_station(self, station_code: str) -> Dict[str, Any]:
        """Get all trains passing through a specific station using RapidAPI IRCTC.

        Args:
            station_code: Station code (e.g., "NDLS" for New Delhi, "BCT" for Mumbai Central)
        
        Returns:
            Dictionary containing list of trains passing through the station
        """
        endpoint = os.getenv("RAIL_TRAINS_BY_STATION_ENDPOINT", "/api/v3/getTrainsByStation")
        params = {
            "stationCode": station_code.upper()
        }
        return self._get(endpoint, params)

    def check_seat_availability(
        self,
        train_number: str,
        from_station: str,
        to_station: str,
        class_type: str,
        quota: str,
        date: str
    ) -> Dict[str, Any]:
        """Check seat availability for a specific train using RapidAPI IRCTC.

        Args:
            train_number: Numeric train number as string (e.g., "19038")
            from_station: Source station code (e.g., "ST")
            to_station: Destination station code (e.g., "BVI")
            class_type: Class type (e.g., "2A", "3A", "SL", "1A", "2S", "CC")
            quota: Quota type (e.g., "GN" for General, "TQ" for Tatkal, "PT" for Premium Tatkal)
            date: Journey date in YYYY-MM-DD, YYYYMMDD format, or relative ("today", "tomorrow")
        
        Returns:
            Dictionary containing seat availability information
        """
        endpoint = os.getenv("RAIL_SEAT_AVAILABILITY_ENDPOINT", "/api/v2/checkSeatAvailability")
        formatted_date = self._normalize_date(date)
        params = {
            "trainNo": train_number,
            "fromStationCode": from_station.upper(),
            "toStationCode": to_station.upper(),
            "classType": class_type.upper(),
            "quota": quota.upper(),
            "dateOfJourney": formatted_date
        }
        return self._get(endpoint, params)

    def get_train_schedule(self, train_number: str) -> Dict[str, Any]:
        """Get complete schedule/route for a specific train using RapidAPI IRCTC.

        Args:
            train_number: Numeric train number as string (e.g., "12936")
        
        Returns:
            Dictionary containing train schedule with all stations, timings, and distances
        """
        endpoint = os.getenv("RAIL_TRAIN_SCHEDULE_ENDPOINT", "/api/v1/getTrainSchedule")
        params = {
            "trainNo": train_number
        }
        return self._get(endpoint, params)

    def get_train_fare(
        self,
        train_number: str,
        from_station: str,
        to_station: str
    ) -> Dict[str, Any]:
        """Get fare information for a specific train between two stations using RapidAPI IRCTC.

        Args:
            train_number: Numeric train number as string (e.g., "19038")
            from_station: Source station code (e.g., "ST")
            to_station: Destination station code (e.g., "BVI")
        
        Returns:
            Dictionary containing fare information for all available classes
        """
        endpoint = os.getenv("RAIL_TRAIN_FARE_ENDPOINT", "/api/v2/getFare")
        params = {
            "trainNo": train_number,
            "fromStationCode": from_station.upper(),
            "toStationCode": to_station.upper()
        }
        return self._get(endpoint, params)


# Service instance - will be initialized when first used
_indian_railways_service = None


def _get_service() -> IndianRailwaysService:
    """Get or create the Indian Railways service instance."""
    global _indian_railways_service
    if _indian_railways_service is None:
        _indian_railways_service = IndianRailwaysService()
    return _indian_railways_service



def get_live_train_status_tool(**kwargs) -> Dict[str, Any]:
    """
    Get live train status tool.
    
    Request Body:
    {
        "train_number": str (required)
        "date": str (required) - YYYY-MM-DD or 'today'/'tomorrow'
    }
    """
    try:
        train_number = kwargs.get('train_number')
        date = kwargs.get('date')
        
        if not all([train_number, date]):
            return {"error": "Missing required parameters: train_number, date"}
        
        
        service = _get_service()
        
        result = service.get_live_train_status(train_number=train_number, date=date)
        
        return result
        
    except Exception as e:
        return {"error": f"Get live train status failed: {str(e)}"}


def search_trains_tool(**kwargs) -> Dict[str, Any]:
    """
    Search trains tool.
    
    Request Body:
    {
        "from_station": str (required) - Station code
        "to_station": str (required) - Station code
        "date": str (required) - YYYY-MM-DD or 'today'/'tomorrow'
    }
    """
    try:
        from_station = kwargs.get('from_station')
        to_station = kwargs.get('to_station')
        date = kwargs.get('date')
        
        if not all([from_station, to_station, date]):
            return {"error": "Missing required parameters: from_station, to_station, date"}
        
        
        service = _get_service()
        
        result = service.search_trains_between_stations(
            from_station=from_station,
            to_station=to_station,
            date=date
        )
        
        return result
        
    except Exception as e:
        return {"error": f"Search trains failed: {str(e)}"}


def get_trains_by_station_tool(**kwargs) -> Dict[str, Any]:
    """
    Get trains by station tool.
    
    Request Body:
    {
        "station_code": str (required)
    }
    """
    try:
        station_code = kwargs.get('station_code')
        
        if not station_code:
            return {"error": "Missing required parameter: station_code"}
        
        
        service = _get_service()
        
        result = service.get_trains_by_station(station_code=station_code)
        
        return result
        
    except Exception as e:
        return {"error": f"Get trains by station failed: {str(e)}"}


def check_seat_availability_tool(**kwargs) -> Dict[str, Any]:
    """
    Check seat availability tool.
    
    Request Body:
    {
        "train_number": str (required)
        "from_station": str (required)
        "to_station": str (required)
        "class_type": str (required) - e.g., "2A", "3A", "SL"
        "quota": str (required) - e.g., "GN", "TQ", "PT"
        "date": str (required) - YYYY-MM-DD
    }
    """
    try:
        train_number = kwargs.get('train_number')
        from_station = kwargs.get('from_station')
        to_station = kwargs.get('to_station')
        class_type = kwargs.get('class_type')
        quota = kwargs.get('quota')
        date = kwargs.get('date')
        
        if not all([train_number, from_station, to_station, class_type, quota, date]):
            return {"error": "Missing required parameters"}
        
        
        service = _get_service()
        
        result = service.check_seat_availability(
            train_number=train_number,
            from_station=from_station,
            to_station=to_station,
            class_type=class_type,
            quota=quota,
            date=date
        )
        
        return result
        
    except Exception as e:
        return {"error": f"Check seat availability failed: {str(e)}"}


def get_train_schedule_tool(**kwargs) -> Dict[str, Any]:
    """
    Get train schedule tool.
    
    Request Body:
    {
        "train_number": str (required)
    }
    """
    try:
        train_number = kwargs.get('train_number')
        
        if not train_number:
            return {"error": "Missing required parameter: train_number"}
        
        
        service = _get_service()
        
        result = service.get_train_schedule(train_number=train_number)
        
        return result
        
    except Exception as e:
        return {"error": f"Get train schedule failed: {str(e)}"}


def get_train_fare_tool(**kwargs) -> Dict[str, Any]:
    """
    Get train fare tool.
    
    Request Body:
    {
        "train_number": str (required)
        "from_station": str (required)
        "to_station": str (required)
    }
    """
    try:
        train_number = kwargs.get('train_number')
        from_station = kwargs.get('from_station')
        to_station = kwargs.get('to_station')
        
        if not all([train_number, from_station, to_station]):
            return {"error": "Missing required parameters"}
        
        
        service = _get_service()
        
        result = service.get_train_fare(
            train_number=train_number,
            from_station=from_station,
            to_station=to_station
        )
        
        return result
        
    except Exception as e:
        return {"error": f"Get train fare failed: {str(e)}"}