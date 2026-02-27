import json
import os
from typing import Dict, Any, List

class ConfigLoader:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.routes: List[Dict[str, Any]] = []
        
    def load(self) -> bool:
        if not os.path.exists(self.config_path):
            return False
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        self.routes = self.config.get('routes', [])
        self.server = self.config.get('server', {})
        return True
    
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