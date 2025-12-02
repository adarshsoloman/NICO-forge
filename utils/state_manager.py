"""State management for resume capability."""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Set
from datetime import datetime


class StateManager:
    """Manage pipeline state for resume capability."""
    
    def __init__(self, state_dir: str = "outputs/.state"):
        """Initialize state manager.
        
        Args:
            state_dir: Directory to store state files
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
    
    def save_state(
        self,
        module_name: str,
        status: str,
        data: Optional[Dict[str, Any]] = None
    ):
        """Save module state.
        
        Args:
            module_name: Name of the module (e.g., 'extraction', 'pipeline')
            status: Current status ('in_progress', 'completed', 'failed')
            data: Additional state data
        """
        state_file = self.state_dir / f"{module_name}.json"
        
        state = {
            "module": module_name,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "data": data or {}
        }
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    
    def load_state(self, module_name: str) -> Optional[Dict[str, Any]]:
        """Load module state.
        
        Args:
            module_name: Name of the module
            
        Returns:
            State dictionary or None if not found
        """
        state_file = self.state_dir / f"{module_name}.json"
        
        if not state_file.exists():
            return None
        
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    def is_completed(self, module_name: str) -> bool:
        """Check if module has completed.
        
        Args:
            module_name: Name of the module
            
        Returns:
            True if module has completed successfully
        """
        state = self.load_state(module_name)
        return state is not None and state.get('status') == 'completed'
    
    def get_completed_ids(self, module_name: str, key: str = "completed_ids") -> Set[Any]:
        """Get set of completed item IDs.
        
        Args:
            module_name: Name of the module
            key: Key in state data containing ID list
            
        Returns:
            Set of completed IDs
        """
        state = self.load_state(module_name)
        if state and 'data' in state and key in state['data']:
            return set(state['data'][key])
        return set()
    
    def update_completed_ids(
        self,
        module_name: str,
        new_ids: Set[Any],
        key: str = "completed_ids"
    ):
        """Update completed IDs in state.
        
        Args:
            module_name: Name of the module
            new_ids: Set of newly completed IDs
            key: Key in state data to update
        """
        state = self.load_state(module_name) or {
            "module": module_name,
            "status": "in_progress",
            "data": {}
        }
        
        existing_ids = set(state.get('data', {}).get(key, []))
        existing_ids.update(new_ids)
        
        state['data'][key] = list(existing_ids)
        state['timestamp'] = datetime.now().isoformat()
        
        self.save_state(module_name, state['status'], state['data'])
    
    def clear_state(self, module_name: Optional[str] = None):
        """Clear state for module or all modules.
        
        Args:
            module_name: Specific module to clear, or None for all
        """
        if module_name:
            state_file = self.state_dir / f"{module_name}.json"
            if state_file.exists():
                state_file.unlink()
        else:
            # Clear all state files
            for state_file in self.state_dir.glob("*.json"):
                state_file.unlink()
