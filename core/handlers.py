import time
from typing import Dict, Any, Optional

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
    
    def _build_response(self, body: str, status: int = 200, 
                        extra_headers: Optional[Dict[str, str]] = None,
                        http_version: str = "HTTP/1.1") -> bytes:
        status_line = f"{http_version} {status} {self._get_reason_phrase(status)}\r\n"
        
        headers = "Content-Type: text/plain\r\n"
        headers += f"Content-Length: {len(body)}\r\n"
        
        if extra_headers:
            for key, value in extra_headers.items():
                headers += f"{key}: {value}\r\n"
        
        response = status_line + headers + "\r\n" + body
        return response.encode('utf-8')
    
    def _get_reason_phrase(self, status: int) -> str:
        phrases = {
            200: 'OK', 201: 'Created', 204: 'No Content',
            301: 'Moved Permanently', 302: 'Found', 304: 'Not Modified',
            400: 'Bad Request', 401: 'Unauthorized', 403: 'Forbidden',
            404: 'Not Found', 405: 'Method Not Allowed', 408: 'Request Timeout',
            500: 'Internal Server Error', 502: 'Bad Gateway',
            503: 'Service Unavailable', 504: 'Gateway Timeout'
        }
        return phrases.get(status, 'Unknown')
    
    def _send_response(self, handler, response: bytes):
        try:
            handler.wfile.write(response)
            handler.wfile.flush()
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to send response: {e}")
    
    def _ignore_connection_close(self, handler) -> bool:
        timeout = self.config.get('timeout', 30)
        status = self.config.get('status', 200)
        body = self.config.get('body', 'Response sent, but connection will be held')
        
        response = self._build_response(body, status)
        self._send_response(handler, response)
        
        if self.logger:
            self.logger.info(f"Ignoring Connection: close, waiting {timeout}s before closing")
        
        time.sleep(timeout)
        return True
    
    def _drop_connection(self, handler) -> bool:
        drop_after_bytes = self.config.get('drop_after_bytes', 0)
        drop_after_time = self.config.get('drop_after_time', 0)
        
        if drop_after_time > 0:
            if self.logger:
                self.logger.info(f"Waiting {drop_after_time}s then dropping connection")
            time.sleep(drop_after_time)
            return True
        
        if drop_after_bytes > 0:
            status = self.config.get('status', 200)
            body = 'A' * drop_after_bytes
            declared_length = self.config.get('declared_length', drop_after_bytes)
            
            status_line = f"HTTP/1.1 {status} OK\r\n"
            response = f"{status_line}Content-Length: {declared_length}\r\n\r\n{body}"
            
            if self.logger:
                self.logger.info(f"Sending {drop_after_bytes} bytes, declared {declared_length}, then dropping")
            
            self._send_response(handler, response.encode('utf-8'))
            return True
        
        return True
    
    def _timeout_before_response(self, handler) -> bool:
        timeout = self.config.get('timeout', 60)
        if self.logger:
            self.logger.info(f"Waiting {timeout}s before any response")
        time.sleep(timeout)
        
        body = self.config.get('body', 'Finally responded')
        status = self.config.get('status', 200)
        response = self._build_response(body, status)
        self._send_response(handler, response)
        return True
    
    def _partial_response(self, handler) -> bool:
        send_bytes = self.config.get('send_bytes', 10)
        status = self.config.get('status', 200)
        status_line = f"HTTP/1.1 {status} OK\r\n"
        
        partial = status_line[:send_bytes]
        
        if self.logger:
            self.logger.info(f"Sent {send_bytes} bytes then dropping")
        
        try:
            handler.wfile.write(partial.encode('utf-8'))
            handler.wfile.flush()
        except Exception:
            pass
        return True
    
    def _no_content_length(self, handler) -> bool:
        status = self.config.get('status', 200)
        body = self.config.get('body', 'No content length header')
        
        response = f"HTTP/1.1 {status} OK\r\nContent-Type: text/plain\r\n\r\n{body}"
        self._send_response(handler, response.encode('utf-8'))
        
        if self.logger:
            self.logger.info("Sent response without Content-Length")
        return True
    
    def _wrong_content_length(self, handler) -> bool:
        status = self.config.get('status', 200)
        body = self.config.get('body', 'Body content')
        declared_length = self.config.get('declared_length', 1000)
        
        response = f"HTTP/1.1 {status} OK\r\nContent-Length: {declared_length}\r\n\r\n{body}"
        self._send_response(handler, response.encode('utf-8'))
        
        if self.logger:
            self.logger.info(f"Declared Content-Length: {declared_length}, actual: {len(body)}")
        return True
    
    def _http10_response(self, handler) -> bool:
        status = self.config.get('status', 200)
        body = self.config.get('body', 'HTTP/1.0 response')
        
        response = self._build_response(body, status, http_version="HTTP/1.0")
        self._send_response(handler, response)
        return True
    
    def _connection_header_test(self, handler) -> bool:
        client_connection = handler.headers.get('Connection', '').lower()
        behavior = self.config.get('behavior', 'ignore')
        
        status = self.config.get('status', 200)
        body = self.config.get('body', f'Client sent Connection: {client_connection}')
        
        extra_headers = {}
        if behavior == 'force_close':
            extra_headers['Connection'] = 'close'
        elif behavior == 'force_keepalive':
            extra_headers['Connection'] = 'keep-alive'
        
        response = self._build_response(body, status, extra_headers)
        self._send_response(handler, response)
        
        hold_time = self.config.get('hold_time', 0)
        if hold_time > 0:
            time.sleep(hold_time)
        
        return True