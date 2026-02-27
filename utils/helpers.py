import time
import re
from datetime import datetime

def format_log(level: str, message: str, client_addr: tuple = None) -> str:
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    client = f"{client_addr[0]}:{client_addr[1]}" if client_addr else "-"
    return f"[{timestamp}] [{level}] [{client}] {message}"

def parse_size(size_str: str) -> int:
    if isinstance(size_str, int):
        return size_str
    match = re.match(r'^(\d+(?:\.\d+)?)(KB|MB|GB)?$', str(size_str).upper())
    if not match:
        return int(size_str)
    value = float(match.group(1))
    unit = match.group(2) or ''
    multipliers = {'': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3}
    return int(value * multipliers.get(unit, 1))