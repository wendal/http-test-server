import gzip
import io
import time
from http import HTTPStatus
from typing import Dict, Any, Optional
from utils.helpers import parse_size

class ResponseGenerator:
    def __init__(self, route_config: Dict[str, Any], logger=None):
        self.config = route_config
        self.logger = logger
        
    def generate(self, handler) -> bytes:
        response_type = self.config.get('type', 'normal')
        
        if response_type == 'normal':
            return self._normal_response()
        elif response_type == 'slow':
            return self._slow_response(handler)
        elif response_type == 'chunked':
            return self._chunked_response(handler)
        elif response_type == 'malformed':
            return self._malformed_response()
        elif response_type == 'large':
            return self._large_response()
        else:
            return self._normal_response()
    
    def _build_status_line(self) -> str:
        status = self.config.get('status', 200)
        reason = self._get_reason_phrase(status)
        return f"HTTP/1.1 {status} {reason}\r\n"
    
    def _get_reason_phrase(self, status: int) -> str:
        try:
            return HTTPStatus(status).phrase
        except ValueError:
            return 'Unknown'
    
    def _build_headers(self) -> str:
        headers = self.config.get('headers', {})
        custom_headers = self.config.get('custom_headers', [])
        
        header_lines = ""
        for key, value in headers.items():
            header_lines += f"{key}: {value}\r\n"
        
        for custom in custom_headers:
            header_lines += f"{custom}\r\n"
        
        if 'Content-Length' not in headers and self.config.get('type') not in ('chunked', 'large'):
            body = self._get_body()
            header_lines += f"Content-Length: {len(body)}\r\n"
        
        return header_lines
    
    def _get_body(self) -> bytes:
        body = self.config.get('body', '')
        if isinstance(body, str):
            return body.encode('utf-8')
        return body
    
    def _normal_response(self) -> bytes:
        status_line = self._build_status_line()
        headers = self._build_headers()
        body = self._get_body()
        
        if not headers.endswith('\r\n'):
            headers += '\r\n'
        
        return (status_line + headers + '\r\n').encode('utf-8') + body
    
    def _slow_response(self, handler) -> bytes:
        delay = self.config.get('delay', 5)
        chunk_size = self.config.get('chunk_size', 100)
        chunk_delay = self.config.get('chunk_delay', 1)
        
        status_line = self._build_status_line()
        headers = self._build_headers()
        body = self._get_body()
        
        if not headers.endswith('\r\n'):
            headers += '\r\n'
        
        if delay > 0:
            time.sleep(delay)
        
        response = (status_line + headers + '\r\n').encode('utf-8')
        handler.wfile.write(response)
        handler.wfile.flush()
        
        for i in range(0, len(body), chunk_size):
            chunk = body[i:i+chunk_size]
            handler.wfile.write(chunk)
            handler.wfile.flush()
            time.sleep(chunk_delay)
        
        return b''
    
    def _chunked_response(self, handler) -> bytes:
        chunks = self.config.get('chunks', ['Hello', ' ', 'World'])
        chunk_delay = self.config.get('chunk_delay', 0)
        
        status_line = self._build_status_line()
        headers = "Transfer-Encoding: chunked\r\n"
        headers += self._build_headers()
        
        if not headers.endswith('\r\n'):
            headers += '\r\n'
        
        response = (status_line + headers + '\r\n').encode('utf-8')
        handler.wfile.write(response)
        handler.wfile.flush()
        
        for chunk in chunks:
            if isinstance(chunk, str):
                chunk = chunk.encode('utf-8')
            chunk_header = f"{len(chunk):X}\r\n".encode('utf-8')
            handler.wfile.write(chunk_header)
            handler.wfile.write(chunk)
            handler.wfile.write(b"\r\n")
            handler.wfile.flush()
            if chunk_delay > 0:
                time.sleep(chunk_delay)
        
        handler.wfile.write(b"0\r\n\r\n")
        handler.wfile.flush()
        return b''
    
    def _malformed_response(self) -> bytes:
        status_line = self._build_status_line()
        headers = ""
        
        malformed_type = self.config.get('malformed_type', 'duplicate_content_length')
        
        if malformed_type == 'duplicate_content_length':
            lengths = self.config.get('content_lengths', [100, 200])
            for length in lengths:
                headers += f"Content-Length: {length}\r\n"
        elif malformed_type == 'invalid_header':
            invalid_headers = self.config.get('invalid_headers', ['X-Bad: value\r\n'])
            for h in invalid_headers:
                headers += h + "\r\n"
        elif malformed_type == 'missing_header_end':
            headers += "Content-Type: text/html\r\n"
            return (status_line + headers).encode('utf-8')
        elif malformed_type == 'no_status_line':
            headers = self._build_headers()
            body = self._get_body()
            return (headers + '\r\n').encode('utf-8') + body
        elif malformed_type == 'invalid_version':
            status_line = "HTTP/0.9 200 OK\r\n"
        
        body = self._get_body()
        if not headers.endswith('\r\n'):
            headers += '\r\n'
        
        return (status_line + headers + '\r\n').encode('utf-8') + body
    
    def _large_response(self) -> bytes:
        size = parse_size(self.config.get('body_size', '1MB'))
        pattern = self.config.get('pattern', 'A')
        
        status_line = self._build_status_line()
        headers = self._build_headers()
        headers += f"Content-Length: {size}\r\n"
        
        if not headers.endswith('\r\n'):
            headers += '\r\n'
        
        header_bytes = (status_line + headers + '\r\n').encode('utf-8')
        body = (pattern * (size // len(pattern) + 1))[:size].encode('utf-8')
        
        return header_bytes + body