import time
import socket
import struct
from typing import Dict, Any
from utils.helpers import parse_size

class SpecialHandlers:
    def __init__(self, route_config: Dict[str, Any], logger=None):
        self.config = route_config
        self.logger = logger
    
    def handle(self, handler) -> bool:
        handler_type = self.config.get('handler_type')
        
        if handler_type == 'ignore_connection_close':
            return self._ignore_connection_close(handler)
        elif handler_type == 'drop_connection':
            return self._drop_connection(handler)
        elif handler_type == 'timeout_before_response':
            return self._timeout_before_response(handler)
        elif handler_type == 'partial_response':
            return self._partial_response(handler)
        elif handler_type == 'no_content_length':
            return self._no_content_length(handler)
        elif handler_type == 'wrong_content_length':
            return self._wrong_content_length(handler)
        elif handler_type == 'http10_response':
            return self._http10_response(handler)
        elif handler_type == 'connection_header_test':
            return self._connection_header_test(handler)
        
        return False
    
    def _ignore_connection_close(self, handler) -> bool:
        timeout = self.config.get('timeout', 30)
        
        status = self.config.get('status', 200)
        body = self.config.get('body', 'Response sent, but connection will be held')
        
        response = f"HTTP/1.1 {status} OK\r\n"
        response += "Content-Type: text/plain\r\n"
        response += f"Content-Length: {len(body)}\r\n"
        response += "\r\n"
        response += body
        
        handler.wfile.write(response.encode('utf-8'))
        handler.wfile.flush()
        
        if self.logger:
            self.logger.info(f"Ignoring Connection: close, waiting {timeout}s before closing")
        
        time.sleep(timeout)
        return True
    
    def _drop_connection(self, handler) -> bool:
        drop_after_bytes = self.config.get('drop_after_bytes', 0)
        drop_after_time = self.config.get('drop_after_time', 0)
        
        if drop_after_time > 0:
            time.sleep(drop_after_time)
            if self.logger:
                self.logger.info(f"Dropping connection after {drop_after_time}s")
            return True
        
        if drop_after_bytes > 0:
            status = self.config.get('status', 200)
            body = 'A' * drop_after_bytes
            
            response = f"HTTP/1.1 {status} OK\r\n"
            response += f"Content-Length: {drop_after_bytes * 10}\r\n"
            response += "\r\n"
            response += body
            
            handler.wfile.write(response.encode('utf-8'))
            handler.wfile.flush()
            
            if self.logger:
                self.logger.info(f"Dropping connection after {drop_after_bytes} bytes")
            return True
        
        return True
    
    def _timeout_before_response(self, handler) -> bool:
        timeout = self.config.get('timeout', 60)
        if self.logger:
            self.logger.info(f"Waiting {timeout}s before any response")
        time.sleep(timeout)
        
        status = self.config.get('status', 200)
        body = self.config.get('body', 'Finally responded')
        response = f"HTTP/1.1 {status} OK\r\n"
        response += f"Content-Length: {len(body)}\r\n"
        response += "\r\n"
        response += body
        
        handler.wfile.write(response.encode('utf-8'))
        handler.wfile.flush()
        return True
    
    def _partial_response(self, handler) -> bool:
        send_bytes = self.config.get('send_bytes', 10)
        
        status = self.config.get('status', 200)
        status_line = f"HTTP/1.1 {status} OK\r\n"
        
        partial = status_line[:send_bytes]
        handler.wfile.write(partial.encode('utf-8'))
        handler.wfile.flush()
        
        if self.logger:
            self.logger.info(f"Sent {send_bytes} bytes then dropping")
        return True
    
    def _no_content_length(self, handler) -> bool:
        status = self.config.get('status', 200)
        body = self.config.get('body', 'No content length header')
        
        response = f"HTTP/1.1 {status} OK\r\n"
        response += "Content-Type: text/plain\r\n"
        response += "\r\n"
        response += body
        
        handler.wfile.write(response.encode('utf-8'))
        handler.wfile.flush()
        
        if self.logger:
            self.logger.info("Sent response without Content-Length")
        return True
    
    def _wrong_content_length(self, handler) -> bool:
        status = self.config.get('status', 200)
        body = self.config.get('body', 'Body content')
        declared_length = self.config.get('declared_length', 1000)
        
        response = f"HTTP/1.1 {status} OK\r\n"
        response += f"Content-Length: {declared_length}\r\n"
        response += "\r\n"
        response += body
        
        handler.wfile.write(response.encode('utf-8'))
        handler.wfile.flush()
        
        if self.logger:
            self.logger.info(f"Declared Content-Length: {declared_length}, actual: {len(body)}")
        return True
    
    def _http10_response(self, handler) -> bool:
        status = self.config.get('status', 200)
        body = self.config.get('body', 'HTTP/1.0 response')
        
        response = f"HTTP/1.0 {status} OK\r\n"
        response += "Content-Type: text/plain\r\n"
        response += f"Content-Length: {len(body)}\r\n"
        response += "\r\n"
        response += body
        
        handler.wfile.write(response.encode('utf-8'))
        handler.wfile.flush()
        return True
    
    def _connection_header_test(self, handler) -> bool:
        client_connection = handler.headers.get('Connection', '').lower()
        behavior = self.config.get('behavior', 'ignore')
        
        status = self.config.get('status', 200)
        body = self.config.get('body', f'Client sent Connection: {client_connection}')
        
        response = f"HTTP/1.1 {status} OK\r\n"
        response += f"Content-Length: {len(body)}\r\n"
        
        if behavior == 'ignore':
            pass
        elif behavior == 'force_close':
            response += "Connection: close\r\n"
        elif behavior == 'force_keepalive':
            response += "Connection: keep-alive\r\n"
        
        response += "\r\n"
        response += body
        
        handler.wfile.write(response.encode('utf-8'))
        handler.wfile.flush()
        
        hold_time = self.config.get('hold_time', 0)
        if hold_time > 0:
            time.sleep(hold_time)
        
        return True