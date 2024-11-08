# core/base_module.py
import dearpygui.dearpygui as dpg
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import json
import logging

class ModuleBase(ABC):
    def __init__(self, module_id: str):
        self.module_id = module_id
        self.module_name = ""
        self.module_description = ""
        self.module_version = "1.0.0"
        self.module_dependencies = []
        self.module_config: Dict[str, Any] = {}
        self.logger = logging.getLogger(module_id)
        self.is_initialized = False
        self.window_tag = f"{module_id}_window"
        
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the module. Must be implemented by child classes."""
        pass

    @abstractmethod
    def update(self) -> None:
        """Update module state. Must be implemented by child classes."""
        pass

    @abstractmethod
    def get_data(self) -> Dict[str, Any]:
        """Return module's data. Must be implemented by child classes."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup module resources. Must be implemented by child classes."""
        pass

    def save_state(self) -> Dict[str, Any]:
        """Save module state to dictionary."""
        return {
            "module_id": self.module_id,
            "config": self.module_config,
            "version": self.module_version
        }

    def load_state(self, state: Dict[str, Any]) -> bool:
        """Load module state from dictionary."""
        try:
            if state["version"] != self.module_version:
                self.logger.warning(f"Version mismatch: saved={state['version']}, current={self.module_version}")
            self.module_config = state.get("config", {})
            return True
        except Exception as e:
            self.logger.error(f"Error loading state: {str(e)}")
            return False

    def create_window(self, x_pos: int = 100, y_pos: int = 100) -> None:
        """Create module's main window."""
        with dpg.window(
            label=self.module_name,
            tag=self.window_tag,
            pos=(x_pos, y_pos),
            width=400,
            height=300,
            collapsed=False
        ):
            self._setup_window_contents()

    @abstractmethod
    def _setup_window_contents(self) -> None:
        """Setup module's window contents. Must be implemented by child classes."""
        pass

    def show_window(self) -> None:
        """Show module's window."""
        dpg.show_item(self.window_tag)

    def hide_window(self) -> None:
        """Hide module's window."""
        dpg.hide_item(self.window_tag)

    def save_config(self, filepath: str) -> bool:
        """Save module configuration to file."""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.module_config, f, indent=4)
            return True
        except Exception as e:
            self.logger.error(f"Error saving config: {str(e)}")
            return False

    def load_config(self, filepath: str) -> bool:
        """Load module configuration from file."""
        try:
            with open(filepath, 'r') as f:
                self.module_config = json.load(f)
            return True
        except Exception as e:
            self.logger.error(f"Error loading config: {str(e)}")
            return False