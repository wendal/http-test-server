#!/usr/bin/env python3
import argparse
import logging
import os
import sys
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import ConfigLoader
from core.router import Router
from core.response import ResponseGenerator
from core.handlers import SpecialHandlers

DEFAULT_TIMEOUT = 30
MAX_REQUEST_SIZE = 1024 * 1024

class HTTPTestHandler(BaseHTTPRequestHandler):
    router: Optional[Router] = None
    logger: Optional[logging.Logger] = None
    
    def log_message(self, format, *args):
        if self.logger:
            message = format % args
            self.logger.info(f"{self.address_string()} - {message}")
    
    def handle(self):
        try:
            super().handle()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Handler error: {e}")
    
    def _handle_route(self, route: Dict[str, Any]):
        if self.logger:
            self.logger.info(f"Matched route: {route.get('id', 'unknown')} - {route.get('path')}")
        
        try:
            if route.get('handler_type'):
                handler = SpecialHandlers(route, self.logger)
                handler.handle(self)
                return
            
            response_gen = ResponseGenerator(route, self.logger)
            response = response_gen.generate(self)
            
            if response:
                self.wfile.write(response)
                self.wfile.flush()
        except BrokenPipeError:
            if self.logger:
                self.logger.warning("Client disconnected")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error handling route: {e}")
            self._send_500(str(e))
    
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
        try:
            self.wfile.write(response)
            self.wfile.flush()
        except Exception:
            pass
    
    def _send_500(self, message: str):
        body = f'{{"error": "Internal server error", "message": "{message}"}}'.encode()
        response = b'HTTP/1.1 500 Internal Server Error\r\n'
        response += b'Content-Type: application/json\r\n'
        response += f'Content-Length: {len(body)}\r\n'.encode()
        response += b'\r\n'
        response += body
        try:
            self.wfile.write(response)
            self.wfile.flush()
        except Exception:
            pass
    
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
    def __init__(self, server_address, RequestHandlerClass, logger: logging.Logger):
        super().__init__(server_address, RequestHandlerClass)
        self.logger = logger
        self.request_timeout = DEFAULT_TIMEOUT
    
    def get_request(self):
        sock, addr = self.socket.accept()
        sock.settimeout(self.request_timeout)
        return sock, addr


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
    parser.add_argument('-t', '--timeout', type=int, default=DEFAULT_TIMEOUT, help='Connection timeout in seconds')
    args = parser.parse_args()
    
    config_path = args.config
    if not os.path.isabs(config_path):
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), config_path)
    
    logger = setup_logging(args.log_level or 'INFO')
    
    config_loader = ConfigLoader(config_path, logger)
    if not config_loader.load():
        logger.error(f"Could not load config from {config_path}")
        sys.exit(1)
    
    server_config = config_loader.get_server_config()
    
    host = args.host or server_config['host']
    port = args.port or server_config['port']
    log_level = args.log_level or server_config.get('log_level', 'INFO')
    
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    HTTPTestHandler.router = Router(config_loader.get_routes())
    HTTPTestHandler.logger = logger
    
    server_address = (host, port)
    httpd = LoggingHTTPServer(server_address, HTTPTestHandler, logger)
    httpd.request_timeout = args.timeout
    
    logger.info(f"HTTP Test Server starting on {host}:{port}")
    logger.info(f"Config file: {config_path}")
    logger.info(f"Routes loaded: {len(config_loader.get_routes())}")
    logger.info(f"Connection timeout: {args.timeout}s")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        httpd.shutdown()


if __name__ == '__main__':
    main()