import os
import json

EVE_LOG_PATH = '/var/log/suricata/eve.json'
CHUNK_BYTES = 256 * 1024
# Stop looking further back than this, so a huge log with few alerts cannot stall every poll.
MAX_SCAN_BYTES = 64 * 1024 * 1024

def iter_lines_reversed(path, chunk_bytes=CHUNK_BYTES, max_bytes=MAX_SCAN_BYTES):
    """Yield the lines of a file from last to first without reading the whole file."""
    with open(path, 'rb') as f:
        f.seek(0, os.SEEK_END)
        position = f.tell()
        stop_at = max(0, position - max_bytes)
        remainder = b''
        while position > stop_at:
            read_size = min(chunk_bytes, position - stop_at)
            position -= read_size
            f.seek(position)
            lines = (f.read(read_size) + remainder).split(b'\n')
            # The first piece may be the tail of a line that starts in the previous chunk.
            remainder = lines.pop(0)
            yield from reversed(lines)
        if position == 0:
            yield remainder

def get_suricata_alerts(limit=25):
    """Safely parse Suricata EVE logs, returning the newest alerts first."""
    eve_path = EVE_LOG_PATH
    alerts = []
    try:
        if not os.path.exists(eve_path):
            return []
        for line in iter_lines_reversed(eve_path):
            if len(alerts) >= limit:
                break
            if b'alert' not in line:
                continue
            try:
                data = json.loads(line.decode('utf-8', errors='ignore'))
            except json.JSONDecodeError:
                continue
            if not isinstance(data, dict) or data.get('event_type') != 'alert':
                continue
            alert = data.get('alert')
            alerts.append({
                'timestamp': str(data.get('timestamp', '')),
                'src_ip': str(data.get('src_ip', '')),
                'signature': str(alert.get('signature', '') if isinstance(alert, dict) else '')
            })
        return alerts
    except Exception as e:
        print(f"Error reading Suricata logs: {e}")
        return []
