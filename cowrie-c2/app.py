import argparse
import os
import sys

from flask import Flask, g, jsonify, redirect, render_template, request, url_for

from database import (
    SESSION_COOKIE_NAME,
    authenticate_user,
    create_session,
    create_user,
    delete_all_user_sessions,
    delete_session_token,
    get_user_count,
    get_user_from_session_tokens,
    init_db,
    parse_session_cookie_value,
)
import cowrie_telemetry
import suricata_telemetry
from cowrie_telemetry import get_cowrie_digested_logs, list_cowrie_log_files, get_specific_cowrie_log
from host_telemetry import run_host_command
from suricata_telemetry import get_suricata_alerts

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'cowrie-c2-dev-secret-change-me')
init_db()

PUBLIC_ROUTES = {'/login', '/setup', '/logout'}


def get_session_tokens_from_cookie():
    raw_value = request.cookies.get(SESSION_COOKIE_NAME, '')
    return parse_session_cookie_value(raw_value)


def set_session_cookie(response, tokens):
    token_list = [token for token in tokens if token]
    if not token_list:
        response.delete_cookie(SESSION_COOKIE_NAME, path='/', httponly=True, samesite='Lax')
        return response
    response.set_cookie(
        SESSION_COOKIE_NAME,
        ','.join(token_list),
        max_age=60 * 60 * 12,
        httponly=True,
        secure=False,
        samesite='Lax',
        path='/',
    )
    return response


@app.before_request
def enforce_auth():
    if request.path.startswith('/static'):
        return None

    if request.path in PUBLIC_ROUTES:
        return None

    if get_user_count() == 0:
        return redirect(url_for('setup_user'))

    session_tokens = get_session_tokens_from_cookie()
    user = get_user_from_session_tokens(session_tokens)
    if not user:
        return redirect(url_for('login'))

    g.current_user = user
    return None


@app.route('/')
def index():
    if get_user_count() == 0:
        return redirect(url_for('setup_user'))
    return redirect(url_for('login'))


@app.route('/setup', methods=['GET', 'POST'])
def setup_user():
    if get_user_count() > 0:
        return redirect(url_for('login'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not username:
            error = 'Username is required.'
        elif len(password) < 12:
            error = 'Password must be at least 12 characters long.'
        elif password != confirm_password:
            error = 'Passwords do not match.'
        elif not create_user(username, password, confirm_password):
            error = 'Unable to create the initial user. Make sure the password matches and no other user exists.'
        else:
            token = create_session(username)
            if token:
                response = redirect(url_for('dashboard'))
                return set_session_cookie(response, [token])
            return redirect(url_for('dashboard'))

    return render_template('setup.html', error=error)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if get_user_count() == 0:
        return redirect(url_for('setup_user'))

    if request.method == 'GET' and getattr(g, 'current_user', None):
        return redirect(url_for('dashboard'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if authenticate_user(username, password):
            existing_tokens = get_session_tokens_from_cookie()
            new_token = create_session(username)
            if new_token:
                tokens = list(dict.fromkeys(existing_tokens + [new_token]))
                response = redirect(url_for('dashboard'))
                return set_session_cookie(response, tokens)
            response = redirect(url_for('dashboard'))
            return response
        error = 'Invalid username or password.'

    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    raw_tokens = get_session_tokens_from_cookie()
    if raw_tokens:
        for token in raw_tokens:
            delete_session_token(token)

    if getattr(g, 'current_user', None):
        delete_all_user_sessions(g.current_user['username'])

    response = redirect(url_for('login'))
    return set_session_cookie(response, [])


@app.route('/dashboard')
def dashboard():
    suricata_alerts = get_suricata_alerts(limit=25)
    cowrie_logs = get_cowrie_digested_logs(limit=50)
    return render_template('dashboard.html', suricata_alerts=suricata_alerts, cowrie_logs=cowrie_logs)


@app.route('/host')
def host_view():
    return render_template('host.html')


@app.route('/api/host/<cmd_type>')
def host_command_api(cmd_type):
    output = run_host_command(cmd_type)
    return jsonify({"command": cmd_type, "output": output})


@app.route('/api/cowrie/stream')
def cowrie_stream_api():
    """API endpoint for live streaming current digested logs."""
    return jsonify(get_cowrie_digested_logs(limit=50))


@app.route('/api/cowrie/files')
def cowrie_files_api():
    """API to list all available Cowrie log files."""
    return jsonify(list_cowrie_log_files())


@app.route('/api/cowrie/file/<path:filename>')
def cowrie_file_drilldown_api(filename):
    """API to view digested events from a specific historical log file."""
    return jsonify(get_specific_cowrie_log(filename, limit=100))


@app.route('/api/suricata/alerts')
def suricata_alerts_api():
    """API endpoint for live polling of recent Suricata alerts."""
    return jsonify(get_suricata_alerts(limit=25))


def resolve_log_path(path, default_filename):
    """Accept either the log file itself or the directory that holds it."""
    path = os.path.abspath(os.path.expanduser(path))
    if os.path.isfile(path) or (path.endswith('.json') and not os.path.isdir(path)):
        return path
    return os.path.join(path, default_filename)


def check_log_path(label, path):
    """Return an error message if the log directory or an existing log file is unreadable, else None."""
    log_dir = os.path.dirname(path)
    if not os.path.isdir(log_dir):
        return f'{label}: directory not found: {log_dir}'
    if not os.access(log_dir, os.R_OK | os.X_OK):
        return f'{label}: no permission to read directory: {log_dir}'
    if os.path.exists(path) and not os.access(path, os.R_OK):
        return f'{label}: no permission to read file: {path}'
    return None


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='Cowrie C2 dashboard')
    parser.add_argument(
        '--cowrie-logs',
        default=cowrie_telemetry.LOG_FILE_PATH,
        help='Cowrie log directory, or the path to cowrie.json (default: %(default)s)',
    )
    parser.add_argument(
        '--suricata-logs',
        default=suricata_telemetry.EVE_LOG_PATH,
        help='Suricata log directory, or the path to eve.json (default: %(default)s)',
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    cowrie_path = resolve_log_path(args.cowrie_logs, 'cowrie.json')
    suricata_path = resolve_log_path(args.suricata_logs, 'eve.json')

    errors = [
        error
        for error in (check_log_path('Cowrie logs', cowrie_path), check_log_path('Suricata logs', suricata_path))
        if error
    ]
    if errors:
        for error in errors:
            print(f'Startup check failed - {error}', file=sys.stderr)
        sys.exit(1)

    cowrie_telemetry.LOG_FILE_PATH = cowrie_path
    suricata_telemetry.EVE_LOG_PATH = suricata_path
    print(f'Cowrie logs:   {cowrie_path}')
    print(f'Suricata logs: {suricata_path}')
    app.run(host='0.0.0.0', port=5000, debug=False)


if __name__ == '__main__':
    main()
