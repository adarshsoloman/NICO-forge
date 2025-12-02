"""Configuration loader with environment variable overrides."""

import os
import yaml
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv

from utils.exceptions import ConfigFileNotFoundError, InvalidConfigError


class ConfigLoader:
    """Load configuration from YAML with env var overrides."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize config loader.
        
        Args:
            config_path: Path to YAML config file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._apply_env_overrides()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file.
        
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigFileNotFoundError: If config file doesn't exist
            InvalidConfigError: If config file is malformed
        """
        if not self.config_path.exists():
            raise ConfigFileNotFoundError(
                f"Config file not found: {self.config_path}"
            )
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not isinstance(config, dict):
                raise InvalidConfigError("Config must be a dictionary")
            
            return config
        
        except yaml.YAMLError as e:
            raise InvalidConfigError(f"Invalid YAML in config file: {e}")
        except Exception as e:
            raise InvalidConfigError(f"Error loading config: {e}")
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides to config."""
        # Load .env file if it exists
        load_dotenv()
        
        # Map of env vars to config paths
        env_mappings = {
            'CHUNK_SIZE': ('pipeline', 'chunk_size'),
            'BATCH_SIZE': ('pipeline', 'batch_size'),
            'CONCURRENCY': ('pipeline', 'concurrency'),
            'FLUSH_EVERY': ('pipeline', 'flush_every'),
            'OPENROUTER_API_KEY': ('translation', 'api_key'),
            'OPENROUTER_BASE_URL': ('translation', 'base_url'),
            'MAX_COST_INR': ('cost', 'abort_threshold'),
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Navigate to the nested config location
                current = self.config
                for key in config_path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                
                # Convert to appropriate type
                final_key = config_path[-1]
                if env_var in ['CHUNK_SIZE', 'BATCH_SIZE', 'CONCURRENCY', 'FLUSH_EVERY', 'MAX_COST_INR']:
                    current[final_key] = int(value)
                else:
                    current[final_key] = value
    
    def get(self, *keys: str, default: Any = None) -> Any:
        """Get nested config value.
        
        Args:
            *keys: Path to config value (e.g., 'pipeline', 'chunk_size')
            default: Default value if key not found
            
        Returns:
            Config value or default
        """
        current = self.config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current
    
    def get_all(self) -> Dict[str, Any]:
        """Get entire configuration.
        
        Returns:
            Complete configuration dictionary
        """
        return self.config.copy()
    
    def validate_required_keys(self, *key_paths: tuple):
        """Validate that required config keys exist.
        
        Args:
            *key_paths: Tuples of key paths to validate
            
        Raises:
            InvalidConfigError: If required key is missing
        """
        for keys in key_paths:
            value = self.get(*keys)
            if value is None:
                raise InvalidConfigError(
                    f"Required config key missing: {'.'.join(keys)}"
                )
