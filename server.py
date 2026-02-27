#!/usr/bin/env python3
import argparse
import json
import logging
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import ConfigLoader
from core.router import Router
from core.response import ResponseGenerator
from core.handlers import SpecialHandlers
from utils.helpers import format_log

class HTTPTestHandler(BaseHTTPRequestHandler):
    router: Optional[Router] = None
    logger: Optional[logging.Logger] = None
    
    def log_message(self, format, *args):
        if self.logger:
            message = format % args
            self.logger.info(f"{self.address_string()} - {message}")
    
    def _handle_route(self, route: Dict[str, Any]):
        if self.logger:
            self.logger.info(f"Matched route: {route.get('id', 'unknown')} - {route.get('path')}")
        
        if route.get('handler_type'):
            handler = SpecialHandlers(route, self.logger)
            handler.handle(self)
            return
        
        response_gen = ResponseGenerator(route, self.logger)
        response = response_gen.generate(self)
        
        if response:
            self.wfile.write(response)
            self.wfile.flush()
    
    def _handle_request(self, method: str):
        if self.logger:
            self.logger.info(f"Request: {method} {self.path}")
        
        if self.router is None:
            self._send_404()
            return
            
        result = self.router.match(self.path, method)
        
        if result:
            route, params = result
            self._handle_route(route)
        else:
            self._send_404()
    
    def _send_404(self):
        body = b'{"error": "Route not found"}'
        response = b'HTTP/1.1 404 Not Found\r\n'
        response += b'Content-Type: application/json\r\n'
        response += f'Content-Length: {len(body)}\r\n'.encode()
        response += b'\r\n'
        response += body
        self.wfile.write(response)
        self.wfile.flush()
    
    def do_GET(self):
        self._handle_request('GET')
    
    def do_POST(self):
        self._handle_request('POST')
    
    def do_PUT(self):
        self._handle_request('PUT')
    
    def do_DELETE(self):
        self._handle_request('DELETE')
    
    def do_HEAD(self):
        self._handle_request('HEAD')
    
    def do_OPTIONS(self):
        self._handle_request('OPTIONS')
    
    def do_PATCH(self):
        self._handle_request('PATCH')


class LoggingHTTPServer(HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, logger):
        super().__init__(server_address, RequestHandlerClass)
        self.logger = logger


def setup_logging(log_level: str = 'INFO') -> logging.Logger:
    logger = logging.getLogger('http-test-server')
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


def main():
    parser = argparse.ArgumentParser(description='HTTP Test Server for Embedded Clients')
    parser.add_argument('-c', '--config', default='config/routes.json', help='Path to config file')
    parser.add_argument('-H', '--host', default=None, help='Host to bind (overrides config)')
    parser.add_argument('-p', '--port', type=int, default=None, help='Port to listen (overrides config)')
    parser.add_argument('-l', '--log-level', default=None, help='Log level (DEBUG, INFO, WARNING, ERROR)')
    args = parser.parse_args()
    
    config_path = args.config
    if not os.path.isabs(config_path):
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), config_path)
    
    config_loader = ConfigLoader(config_path)
    if not config_loader.load():
        print(f"Error: Could not load config from {config_path}")
        sys.exit(1)
    
    server_config = config_loader.get_server_config()
    
    host = args.host or server_config['host']
    port = args.port or server_config['port']
    log_level = args.log_level or server_config['log_level']
    
    logger = setup_logging(log_level)
    
    HTTPTestHandler.router = Router(config_loader.get_routes())
    HTTPTestHandler.logger = logger
    
    server_address = (host, port)
    httpd = LoggingHTTPServer(server_address, HTTPTestHandler, logger)
    
    logger.info(f"HTTP Test Server starting on {host}:{port}")
    logger.info(f"Config file: {config_path}")
    logger.info(f"Routes loaded: {len(config_loader.get_routes())}")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        httpd.shutdown()


if __name__ == '__main__':
    main()