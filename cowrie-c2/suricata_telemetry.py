import os
import json

def get_suricata_alerts(limit=25):
    """Safely parse Suricata EVE logs."""
    eve_path = '/var/log/suricata/eve.json'
    alerts = []
    try:
        if not os.path.exists(eve_path):
            return []
        with open(eve_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get('event_type') == 'alert':
                        alerts.append({
                            'timestamp': str(data.get('timestamp', '')),
                            'src_ip': str(data.get('src_ip', '')),
                            'signature': str(data.get('alert', {}).get('signature', ''))
                        })
                except json.JSONDecodeError:
                    continue
        return alerts[-limit:][::-1]
    except Exception:
        return []
