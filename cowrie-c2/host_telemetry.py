import os
import subprocess

def read_log_lines(filepath, n=50):
    try:
        if not os.path.exists(filepath):
            return []
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        return [line.strip() for line in lines[-n:]]
    except Exception:
        return []

def run_host_command(cmd_type):
    """Execute whitelisted host commands safely with timeouts and sudo for socket access."""
    if cmd_type == 'fail2ban_logs':
        path = '/var/log/fail2ban.log'
        lines = read_log_lines(path, 30)
        return "\n".join(lines) if lines else "No Fail2Ban log found at /var/log/fail2ban.log."

    commands = {
        'w': ['w'],
        'last': ['last', '-n', '10'],
        'fail2ban_status': ['sudo', 'fail2ban-client', 'status'],
        'fail2ban_sshd': ['sudo', 'fail2ban-client', 'status', 'sshd'],
        'docker_ps': ['docker', 'ps']
    }
    
    if cmd_type not in commands:
        return "Error: Command not allowed."
        
    try:
        result = subprocess.run(
            commands[cmd_type], 
            capture_output=True, 
            text=True, 
            timeout=3
        )
        if result.returncode == 0:
            return result.stdout if result.stdout else "Command executed successfully with no output."
        else:
            return f"Error (Exit {result.returncode}): {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out."
    except Exception as e:
        return f"Exception: {str(e)}"
