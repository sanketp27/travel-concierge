# State Management Architecture

## Overview

This document describes the state management architecture that enforces the global rules where **Root Agent is the only state writer**.

## Key Principles

1. **Root Agent is the only state writer** - Only the Root Agent can commit updates to global state
2. **State persists across queries** - State is stored per session and persists across user messages
3. **Other agents propose changes** - Planner, Follower, and Final agents can only propose state updates
4. **User intention always recorded** - All user intentions are recorded under `state.tasks`

## Architecture Components

### 1. StateManager (`src/state_manager.py`)

The `StateManager` class handles all state operations:

- **Session-specific storage**: State is stored per session in the SQLCache
- **Load state**: Loads state from cache (session-specific) or template file
- **Update state**: Only Root Agent can call `update_state()`
- **Get state**: Provides read-only copy of current state
- **Proposed state diff**: Generates diffs for proposed updates (for other agents)

### 2. Root Agent (`main_agent.py::_root_agent`)

**Responsibilities:**
- Interpret every new user message
- Extract intent, high-level task, required modifications
- Update global state:
  - Add task description to `state.tasks`
  - Add missing fields to `state.travel_info` (origin, date, etc.)
  - Modify fields where required
  - Update `state.user_profile` if preferences mentioned
- Forward enriched state + message to next agent

**State Updates:**
- Records user intention in `state.tasks` with:
  - `task_id`: Unique identifier
  - `timestamp`: When task was created
  - `agent_origin`: "root_agent"
  - `intent`: User's intent (e.g., "flight_search", "complete_trip")
  - `status`: "in_progress"
  - `metadata`: User query, extracted info, reasoning

### 3. Planner Agent (`main_agent.py::_travel_planner`)

**Capabilities:**
- Read current state
- Suggest necessary updates
- Add subtasks
- **Cannot directly modify state** - only proposes changes

**Returns:**
- `task_structure`: Task structure for execution
- `proposed_state_diff`: Proposed state updates (e.g., subtasks to add to `state.tasks`)

**Root Agent commits** the proposed updates after receiving them.

### 4. Next Steps Agent / Follower (`main_agent.py::_determine_next_steps`)

**Capabilities:**
- Read current state
- Suggest necessary updates
- Add subtasks
- Annotate user intention
- **Cannot directly modify state** - only proposes changes

**Returns:**
- `next_steps`: Next steps decision
- `proposed_state_diff`: Proposed state updates (e.g., insights as annotations)

**Root Agent commits** the proposed updates after receiving them.

### 5. Final Agent (`main_agent.py::_generate_final_summary`)

**Capabilities:**
- Read current state
- Propose state updates (e.g., mark tasks as done)
- **Cannot directly modify state** - only proposes changes

**Returns:**
- `summary`: Final user-friendly summary
- `proposed_state_diff`: Proposed state updates (e.g., mark all tasks as "done")

**Root Agent commits** the proposed updates after receiving them.

## State Structure

The state follows the structure defined in `default.json`:

```json
{
  "state": {
    "user_profile": {
      "passport_nationality": "",
      "seat_preference": "",
      "food_preference": "",
      "allergies": [],
      "likes": [],
      "dislikes": [],
      "price_sensitivity": [],
      "home": {
        "event_type": "home",
        "address": "",
        "local_prefer_mode": ""
      }
    },
    "tasks": [
      {
        "task_id": "",
        "timestamp": "",
        "agent_origin": "",
        "intent": "",
        "status": "pending | in_progress | done",
        "metadata": {}
      }
    ],
    "travel_info": {
      "origin": "",
      "destination": "",
      "start_date": "",
      "end_date": "",
      "itinerary": {},
      "outbound": {
        "flight_selection": "",
        "seat_number": ""
      },
      "return": {
        "flight_selection": "",
        "seat_number": ""
      },
      "hotel": {
        "hotel_selection": "",
        "room_selection": ""
      },
      "poi": [],
      "itinerary_datetime": "",
      "itinerary_start_date": "",
      "itinerary_end_date": ""
    }
  }
}
```

## Flow Diagram

```
User Message
    ↓
Root Agent
    ├─ Load current state
    ├─ Analyze user message
    ├─ Extract intent & info
    ├─ Update state.tasks (user intention)
    ├─ Update state.travel_info
    ├─ Update state.user_profile
    └─ Save state
    ↓
Planner Agent (receives state)
    ├─ Read current state
    ├─ Create task structure
    ├─ Propose state updates (subtasks)
    └─ Return: task_structure + proposed_state_diff
    ↓
Root Agent commits planner's proposals
    ↓
Execute Tasks
    ↓
Next Steps Agent (receives state)
    ├─ Read current state
    ├─ Analyze completed tasks
    ├─ Propose state updates (insights, annotations)
    └─ Return: next_steps + proposed_state_diff
    ↓
Root Agent commits next steps proposals
    ↓
Final Agent (receives state)
    ├─ Read current state
    ├─ Generate summary
    ├─ Propose state updates (mark tasks as done)
    └─ Return: summary + proposed_state_diff
    ↓
Root Agent commits final proposals
    ↓
Return response to user
```

## State Persistence

- **Per-session storage**: State is stored in SQLCache with key `state_{session_id}`
- **Persistence**: State persists across queries within the same session
- **Template file**: `default.json` serves as a template for initial state structure
- **Session isolation**: Each session has its own state

## Implementation Details

### StateManager Methods

- `get_state()`: Returns read-only copy of current state
- `update_state(updates)`: Updates state (only Root Agent should call this)
- `add_task(task)`: Convenience method to add task to state.tasks
- `update_travel_info(updates)`: Convenience method to update travel_info
- `update_user_profile(updates)`: Convenience method to update user_profile
- `get_proposed_state_diff(proposed_updates)`: Generates state diff for proposed updates
- `_save_state()`: Saves state to cache (session-specific)

### Deep Merge Logic

The `_deep_merge` method handles:
- **Dictionary merging**: Recursively merges nested dictionaries
- **Task list updates**: 
  - Updates existing tasks by `task_id`
  - Appends new tasks
  - Handles partial task updates (e.g., status updates)

## Benefits

1. **Single source of truth**: Root Agent is the only state writer
2. **State persistence**: State persists across queries
3. **Separation of concerns**: Other agents propose, Root Agent decides
4. **Traceability**: All user intentions recorded in `state.tasks`
5. **Session isolation**: Each session has its own state
6. **Flexibility**: Other agents can propose updates without directly modifying state

