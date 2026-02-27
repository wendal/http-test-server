import re
from typing import Dict, Any, List, Optional, Tuple

class Router:
    def __init__(self, routes: List[Dict[str, Any]]):
        self.routes = routes
        
    def match(self, path: str, method: str = 'GET') -> Optional[Tuple[Dict[str, Any], Dict[str, str]]]:
        for route in self.routes:
            route_path = route.get('path', '')
            route_methods = route.get('methods', ['GET'])
            
            if method.upper() not in [m.upper() for m in route_methods]:
                continue
                
            params = {}
            if self._match_path(route_path, path, params):
                return route, params
        return None
    
    def _match_path(self, pattern: str, path: str, params: Dict[str, str]) -> bool:
        if pattern == path:
            return True
        
        regex = re.sub(r'\{(\w+)\}', r'(?P<\1>[^/]+)', pattern)
        regex = f'^{regex}$'
        match = re.match(regex, path)
        if match:
            params.update(match.groupdict())
            return True
        return False
    
    def get_route_by_id(self, route_id: str) -> Optional[Dict[str, Any]]:
        for route in self.routes:
            if route.get('id') == route_id:
                return route
        return None