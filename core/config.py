import json
import os
import logging
from typing import Dict, Any, List, Optional

class ConfigLoader:
    def __init__(self, config_path: str, logger: Optional[logging.Logger] = None):
        self.config_path = config_path
        self.logger = logger
        self.config: Dict[str, Any] = {}
        self.routes: List[Dict[str, Any]] = []
        self.server: Dict[str, Any] = {}
        
    def load(self) -> bool:
        if not os.path.exists(self.config_path):
            if self.logger:
                self.logger.error(f"Config file not found: {self.config_path}")
            return False
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            self.routes = self.config.get('routes', [])
            self.server = self.config.get('server', {})
            self._validate_routes()
            return True
        except json.JSONDecodeError as e:
            if self.logger:
                self.logger.error(f"Invalid JSON in config file: {e}")
            return False
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to load config: {e}")
            return False
    
    def _validate_routes(self):
        for i, route in enumerate(self.routes):
            route_id = route.get('id', f'route_{i}')
            if 'path' not in route:
                if self.logger:
                    self.logger.warning(f"Route '{route_id}' missing 'path' field")
    
    def get_routes(self) -> List[Dict[str, Any]]:
        return self.routes
    
    def get_server_config(self) -> Dict[str, Any]:
        return {
            'host': self.server.get('host', '0.0.0.0'),
            'port': self.server.get('port', 8080),
            'log_level': self.server.get('log_level', 'INFO')
        }
    
    def get_route_by_id(self, route_id: str) -> Dict[str, Any] | None:
        for route in self.routes:
            if route.get('id') == route_id:
                return route
        return None