# core/state_manager.py
from typing import Dict, Any, Optional, List, Set
import threading
import json
import logging
from datetime import datetime
from dataclasses import dataclass, asdict
from core.event_system import event_system, Event, EventTypes

@dataclass
class StateValue:
    """Container for state values with metadata"""
    value: Any
    timestamp: datetime
    source: str
    ttl: Optional[int] = None  # Time to live in seconds
    persistent: bool = True    # Whether to save to disk

class StateManager:
    """
    Manages shared state between modules
    Handles state updates, persistence, and notifications
    """
    def __init__(self):
        self._state: Dict[str, StateValue] = {}
        self._lock = threading.RLock()
        self._watchers: Dict[str, Set[str]] = {}  # key -> set of module_ids
        self.logger = logging.getLogger("StateManager")

    def set_state(self, key: str, value: Any, source: str, 
                 ttl: Optional[int] = None, persistent: bool = True) -> bool:
        """
        Set a state value
        Args:
            key: State key
            value: State value
            source: Module setting the state
            ttl: Time to live in seconds
            persistent: Whether to save to disk
        Returns:
            bool: Success
        """
        try:
            with self._lock:
                state_value = StateValue(
                    value=value,
                    timestamp=datetime.utcnow(),
                    source=source,
                    ttl=ttl,
                    persistent=persistent
                )
                old_value = self._state.get(key)
                self._state[key] = state_value

                # Publish state change event
                event_system.publish(Event(
                    type=EventTypes.STATE_CHANGED,
                    data={
                        "key": key,
                        "old_value": old_value.value if old_value else None,
                        "new_value": value,
                        "source": source
                    },
                    source="StateManager"
                ))

                # Notify watchers
                self._notify_watchers(key, state_value)
                
                return True
        except Exception as e:
            self.logger.error(f"Error setting state {key}: {str(e)}")
            return False

    def get_state(self, key: str, default: Any = None) -> Any:
        """
        Get a state value
        Args:
            key: State key
            default: Default value if key doesn't exist
        Returns:
            State value or default
        """
        with self._lock:
            state_value = self._state.get(key)
            if state_value is None:
                return default
            
            # Check TTL
            if state_value.ttl is not None:
                age = (datetime.utcnow() - state_value.timestamp).total_seconds()
                if age > state_value.ttl:
                    del self._state[key]
                    return default
                
            return state_value.value

    def watch_state(self, key: str, module_id: str):
        """
        Register a module to watch a state key
        Args:
            key: State key to watch
            module_id: Module ID watching the state
        """
        with self._lock:
            if key not in self._watchers:
                self._watchers[key] = set()
            self._watchers[key].add(module_id)

    def unwatch_state(self, key: str, module_id: str):
        """
        Unregister a module from watching a state key
        Args:
            key: State key to unwatch
            module_id: Module ID to unregister
        """
        with self._lock:
            if key in self._watchers:
                self._watchers[key].discard(module_id)
                if not self._watchers[key]:
                    del self._watchers[key]

    def _notify_watchers(self, key: str, state_value: StateValue):
        """
        Notify modules watching a state key
        Args:
            key: State key that changed
            state_value: New state value
        """
        if key in self._watchers:
            for module_id in self._watchers[key]:
                event_system.publish(Event(
                    type=EventTypes.STATE_WATCH_NOTIFICATION,
                    data={
                        "key": key,
                        "value": state_value.value,
                        "timestamp": state_value.timestamp,
                        "source": state_value.source
                    },
                    source="StateManager"
                ))

    def save_state(self, filepath: str) -> bool:
        """
        Save persistent state to file
        Args:
            filepath: Path to save state
        Returns:
            bool: Success
        """
        try:
            with self._lock:
                persistent_state = {
                    key: asdict(value) for key, value in self._state.items()
                    if value.persistent
                }
                
                with open(filepath, 'w') as f:
                    json.dump(persistent_state, f, indent=4, default=str)
                return True
        except Exception as e:
            self.logger.error(f"Error saving state: {str(e)}")
            return False

    def load_state(self, filepath: str) -> bool:
        """
        Load state from file
        Args:
            filepath: Path to load state from
        Returns:
            bool: Success
        """
        try:
            with open(filepath, 'r') as f:
                loaded_state = json.load(f)
                
            with self._lock:
                for key, value_dict in loaded_state.items():
                    value_dict['timestamp'] = datetime.fromisoformat(value_dict['timestamp'])
                    self._state[key] = StateValue(**value_dict)
                return True
        except Exception as e:
            self.logger.error(f"Error loading state: {str(e)}")
            return False

    def clear_state(self, source: Optional[str] = None):
        """
        Clear all state or state from a specific source
        Args:
            source: Optional source to clear state for
        """
        with self._lock:
            if source:
                self._state = {
                    key: value for key, value in self._state.items()
                    if value.source != source
                }
            else:
                self._state.clear()

    def get_state_info(self) -> Dict[str, Any]:
        """
        Get information about current state
        Returns:
            Dict with state information
        """
        with self._lock:
            return {
                "total_keys": len(self._state),
                "watchers": {k: len(v) for k, v in self._watchers.items()},
                "sources": list(set(v.source for v in self._state.values())),
                "keys": list(self._state.keys())
            }

# Global state manager instance
state_manager = StateManager()
