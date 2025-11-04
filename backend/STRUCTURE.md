# backendCode - Complete Directory Structure

This document provides a comprehensive overview of the `backendCode` directory structure for the Travel Agent API.

```
backendCode/
├── app.py                          # Flask application entry point & REST API
├── config.env                      # Environment variables configuration
├── requirements.txt                # Python dependencies
├── Dockerfile.bin                  # Docker container definition
├── start.sh                        # Application startup script
├── pip_build.sh                    # Dependency installation script
│
├── src/                            # Core source code modules
│   ├── main_agent.py              # Main TravelAgent orchestrator class
│   ├── root_agent.py              # Root agent for query analysis
│   ├── chat_history.py            # SQLite-based chat history & session management
│   └── tools_resgistry.py         # Unified tool registry & execution wrapper
│
├── tools/                          # External API integration tools
│   ├── __init__.py
│   ├── amadeus_flights.py         # Amadeus Flight Search API integration
│   ├── amadeus_hotels.py          # Amadeus Hotel Search API integration
│   ├── indian_railways.py         # Indian Railways (IRCTC) API integration
│   └── map_tools.py               # Google Maps Platform APIs (Places, Routes, Weather)
│
├── schema/                         # Data models & API structure definitions
│   ├── api_structure.py           # Unified travel API structure definitions
│   └── travel_classes.py          # Task, TaskIteration dataclasses
│
└── promptStore/                   # LLM prompt templates
    └── agent_prompt.py            # Prompt generation for TravelAgent
```

## File Descriptions

### Core Application Files

**app.py** (422 lines)
- Flask REST API server
- Endpoints: `/`, `/health`, `/getSession`, `/chat`, `/clearSession`
- CORS configuration for Cloud Run deployment
- Error handling & request logging

**config.env**
- Environment variables for API keys and configuration
- Includes: GEMINI_API_KEY, AMADEUS credentials, GOOGLE_MAPS_API_KEY, etc.

**requirements.txt**
- Python package dependencies
- Flask, Google Generative AI, LangChain, Requests, etc.

### Source Modules (`src/`)

**main_agent.py** (629 lines)
- `TravelAgent` class - Main orchestrator
- Handles session management, task planning, concurrent execution
- Integrates with LLM for travel planning decisions
- Manages iterations and task execution flow

**root_agent.py**
- Root agent for initial query analysis
- Determines if sufficient information exists to proceed
- Handles clarification requests

**chat_history.py** (276 lines)
- `SQLCache` class - SQLite-based session cache
- `SessionMessages` class - Chat message management
- Per-session data persistence

**tools_resgistry.py** (101 lines)
- `TOOL_REGISTRY` - Centralized tool mapping
- `execute_tool_by_name()` - Tool execution wrapper with error handling
- Supports flights, hotels, trains, maps tools

### Tool Integrations (`tools/`)

**amadeus_flights.py** (545 lines)
- `AmadeusFlightsService` - OAuth2 authentication & API client
- Tools: `search_flights_tool`, `get_flight_offers_tool`, `confirm_flight_pricing_tool`, etc.

**amadeus_hotels.py** (184 lines)
- `AmadeusHotelsService` - Hotel search API client
- Tools: `search_hotels_tool`, `get_hotel_details_tool`

**indian_railways.py** (474 lines)
- `IndianRailwaysService` - RapidAPI IRCTC integration
- Tools: `search_trains_tool`, `get_live_train_status_tool`, `check_seat_availability_tool`, etc.

**map_tools.py** (426 lines)
- `GoogleMapsService` - Google Maps Platform APIs
- Tools: `find_places_tool`, `get_place_details_tool`, `get_route_tool`, `get_weather_forecast_tool`, etc.

### Schema Definitions (`schema/`)

**api_structure.py**
- `UNIFIED_TRAVEL_API` - Centralized API function definitions
- Schema for all available travel APIs and their parameters

**travel_classes.py** (82 lines)
- `Task` dataclass - Represents a single API call task
- `TaskIteration` dataclass - Represents one execution iteration

### Prompts (`promptStore/`)

**agent_prompt.py** (566 lines)
- `TravelAgentPrompts` class
- Generates prompts for root agent, travel planner, and next steps
- Formats API documentation for LLM consumption

### Deployment Files

**Dockerfile.bin**
- Container image definition for deployment

**start.sh**
- Application startup script with environment setup

**pip_build.sh**
- Dependency installation script

## Architecture Flow

```
User Request
    ↓
app.py (REST API)
    ↓
main_agent.py (TravelAgent)
    ↓
root_agent.py → Determine if info sufficient
    ↓
travel_planner → Create task structure
    ↓
tools_resgistry.py → Execute tools concurrently
    ↓
tools/* → Call external APIs
    ↓
Response aggregation & formatting
    ↓
Return to user
```

## Key Features

- **Session Management**: Per-user session isolation with SQLite caching
- **Concurrent Execution**: Parallel task execution with ThreadPoolExecutor
- **Error Handling**: Comprehensive error handling and retry logic
- **Tool Abstraction**: Unified tool registry pattern for easy extension
- **Cloud Run Ready**: Configured for Google Cloud Run deployment

## Environment Variables Required

See `config.env` for complete list:
- `GEMINI_API_KEY` - Google Gemini AI API key
- `AMADEUS_CLIENT_ID` / `AMADEUS_CLIENT_SECRET` - Amadeus API credentials
- `GOOGLE_MAPS_API_KEY` - Google Maps Platform API key
- `RAIL_API_KEY` - RapidAPI IRCTC key
- `PORT`, `DEBUG`, `ENVIRONMENT` - Application configuration