"""
State Manager - Handles persistent state management for travel agent
Root Agent is the only state writer - all state updates go through this manager
"""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import copy

class StateManager:
    """Manages persistent state storage and retrieval per session"""
    
    def __init__(self, session_id: str, state_file_path: str = None, cache: Any = None):
        """
        Initialize StateManager for a session
        
        Args:
            session_id: Unique session identifier
            state_file_path: Optional path to state file (defaults to default.json in src/)
            cache: Optional cache instance for session-based storage
        """
        self.session_id = session_id
        self.cache = cache
        
        if state_file_path is None:
            # Default to src/default.json (template)
            script_dir = Path(__file__).parent
            state_file_path = script_dir / "default.json"
        
        self.state_file_path = Path(state_file_path)
        self.template_state_file = self.state_file_path
        
        # Ensure template state file exists
        self._ensure_state_file_exists()
        
        # Load initial state (from cache if available, otherwise from template)
        self.state = self._load_state()
    
    def _ensure_state_file_exists(self):
        """
        Ensure template state file exists with default structure.
        This file is ONLY a template - actual session data is stored in cache.
        """
        if not self.template_state_file.exists():
            # Create default state structure template
            default_state = {
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
                    "tasks": [],
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
            
            # Write default state template (only if file doesn't exist)
            # This is a template file - session-specific data is stored in cache
            with open(self.template_state_file, 'w') as f:
                json.dump(default_state, f, indent=2)
    
    def _load_state(self) -> Dict[str, Any]:
        """Load state from cache (session-specific) or template file"""
        try:
            # Try to load from cache first (session-specific)
            if self.cache:
                cached_state = self.cache.get(f"state_{self.session_id}", self.session_id)
                if cached_state:
                    return cached_state
            
            # Fallback to template file
            if self.template_state_file.exists():
                with open(self.template_state_file, 'r') as f:
                    data = json.load(f)
                    return data.get("state", self._get_default_state())
            
            # Return default state structure
            return self._get_default_state()
        except Exception as e:
            print(f"⚠️ Error loading state: {e}")
            return self._get_default_state()
    
    def _get_default_state(self) -> Dict[str, Any]:
        """Get default state structure"""
        return {
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
            "tasks": [],
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
    
    def get_state(self) -> Dict[str, Any]:
        """Get current state (read-only copy)"""
        return copy.deepcopy(self.state)
    
    def update_state(self, updates: Dict[str, Any]) -> bool:
        """
        Update state with provided updates (only Root Agent should call this)
        
        Args:
            updates: Dictionary with state updates (can be partial)
            
        Returns:
            bool: True if update successful
        """
        try:
            # Deep merge updates into state
            self._deep_merge(self.state, updates)
            
            # Save to file
            return self._save_state()
        except Exception as e:
            print(f"❌ Error updating state: {e}")
            return False
    
    def _deep_merge(self, base: Dict[str, Any], updates: Dict[str, Any]):
        """Deep merge updates into base dictionary"""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                # Recursively merge dictionaries
                self._deep_merge(base[key], value)
            elif key == "tasks" and isinstance(base.get(key), list):
                if isinstance(value, list):
                    # For tasks list, handle updates intelligently
                    existing_task_ids = {task.get("task_id") for task in base[key] if task.get("task_id")}
                    for task in value:
                        task_id = task.get("task_id")
                        if task_id and task_id in existing_task_ids:
                            # Update existing task (merge metadata, update status)
                            existing_task = next(t for t in base[key] if t.get("task_id") == task_id)
                            existing_task.update(task)
                        elif task_id:
                            # New task with task_id
                            base[key].append(task)
                        else:
                            # New task without task_id (Root Agent should generate one)
                            base[key].append(task)
                else:
                    base[key] = value
            else:
                # Replace or set value
                base[key] = value
    
    def add_task(self, task: Dict[str, Any]) -> bool:
        """
        Add a task to state.tasks (convenience method for Root Agent)
        
        Args:
            task: Task dictionary with task_id, timestamp, agent_origin, intent, status, metadata
            
        Returns:
            bool: True if task added successfully
        """
        if "tasks" not in self.state:
            self.state["tasks"] = []
        
        # Ensure required fields
        if "task_id" not in task or not task["task_id"]:
            task["task_id"] = f"task_{datetime.now().timestamp()}_{len(self.state['tasks'])}"
        
        if "timestamp" not in task:
            task["timestamp"] = datetime.now().isoformat()
        
        if "status" not in task:
            task["status"] = "pending"
        
        # Check if task already exists
        existing_task_ids = {t.get("task_id") for t in self.state["tasks"]}
        if task["task_id"] not in existing_task_ids:
            self.state["tasks"].append(task)
            return self._save_state()
        
        return False
    
    def update_travel_info(self, travel_info_updates: Dict[str, Any]) -> bool:
        """
        Update travel_info in state (convenience method for Root Agent)
        
        Args:
            travel_info_updates: Dictionary with travel_info updates
            
        Returns:
            bool: True if update successful
        """
        if "travel_info" not in self.state:
            self.state["travel_info"] = {}
        
        self._deep_merge(self.state["travel_info"], travel_info_updates)
        return self._save_state()
    
    def update_user_profile(self, profile_updates: Dict[str, Any]) -> bool:
        """
        Update user_profile in state (convenience method for Root Agent)
        
        Args:
            profile_updates: Dictionary with user_profile updates
            
        Returns:
            bool: True if update successful
        """
        if "user_profile" not in self.state:
            self.state["user_profile"] = {}
        
        self._deep_merge(self.state["user_profile"], profile_updates)
        return self._save_state()
    
    def _save_state(self) -> bool:
        """
        Save state to cache (session-specific) only.
        DO NOT write session data to default.json - it's a template file only.
        """
        try:
            # Ensure all state data is JSON serializable
            # Convert any non-serializable objects to dicts
            serializable_state = self._make_json_serializable(self.state)
            
            # Save to cache (session-specific persistence)
            # This is the ONLY place where session state should be stored
            if self.cache:
                self.cache.set(f"state_{self.session_id}", serializable_state, self.session_id)
                return True
            else:
                print("⚠️ Warning: No cache available, state will not persist")
                return False
            
        except Exception as e:
            print(f"❌ Error saving state: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _make_json_serializable(self, obj: Any) -> Any:
        """Recursively convert objects to JSON-serializable format"""
        if isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        else:
            # For any other type, try to convert to dict or string
            if hasattr(obj, '__dict__'):
                return self._make_json_serializable(obj.__dict__)
            elif hasattr(obj, 'to_dict'):
                return self._make_json_serializable(obj.to_dict())
            else:
                return str(obj)
    
    def get_proposed_state_diff(self, proposed_updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a state diff from proposed updates (for other agents to use)
        This doesn't modify state, just shows what would change
        
        Args:
            proposed_updates: Proposed state updates
            
        Returns:
            Dict: State diff showing proposed changes
        """
        current_state = self.get_state()
        proposed_state = copy.deepcopy(current_state)
        
        # Apply proposed updates to proposed_state
        self._deep_merge(proposed_state, proposed_updates)
        
        # Generate diff (simplified - just return the proposed updates)
        return {
            "proposed_updates": proposed_updates,
            "current_state": current_state,
            "proposed_state": proposed_state
        }

