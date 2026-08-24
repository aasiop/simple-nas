from flask import Flask, jsonify, request, send_from_directory, session, redirect #session stores user session data (a dictionary assigned to the user)
import os
import time
import re
import secrets
from dotenv import load_dotenv
from werkzeug.security import check_password_hash #Flask is built on Werkzeug, so it is already installed
import subprocess

load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = os.environ.get('SECRET_KEY') #data stored in the cookie

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SMB_CONF_PATH = '/etc/samba/smb.conf'


#ip, (number of consecutive failed attempts, until when it is locked - timestamp)
failed_logins = {}
MAX_ATTEMPTS = 5
LOCK_SECONDS = 300

def is_locked(ip):
    count, locked_until = failed_logins.get(ip, (0, 0)) #gets the number of failed logins, if there is no entry (first login), it returns (0,0)
    return time.time() < locked_until #smaller = true, greater = false

def register_failed_attempt(ip): #called after a failed attempt
    count, _ = failed_logins.get(ip, (0, 0)) #ip, (błędy, blokada)
    count += 1
    if count >= MAX_ATTEMPTS:
        failed_logins[ip] = (count, time.time() + LOCK_SECONDS)
    else:
        failed_logins[ip] = (count, 0)

def clear_failed_attempts(ip):
    failed_logins.pop(ip, None)

def login_required(view):
    def wrapped(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect('/login') #not logged in
        return view(*args, **kwargs) #logged in
    wrapped.__name__ = view.__name__ #Flask requires a unique function name for each route instead of all of them being named wrapped
    return wrapped

def csrf_protect(view): #decorator - protect modifying actions (CSRF)
    def wrapped(*args, **kwargs):
        session_token = session.get('csrf_token') #used as true/false - if able to retrieve token
        header_token = request.headers.get('X-CSRF-Token') #used as true/false - retrieves token from the request header
        if not session_token or not header_token or not secrets.compare_digest(session_token, header_token):
            return jsonify({'error': 'bad csrf token'}), 403 #403 - forbidden (the request was recognized but access was denied)
        return view(*args, **kwargs)
    wrapped.__name__ = view.__name__
    return wrapped

@app.route('/login', methods=['GET', 'POST']) #GET - someone wants to see the form, POST - someone wants to log in
def login():
    if request.method == 'POST':
        ip = request.remote_addr #IP address from which the request came, Flask retrieves it from TCP

        if is_locked(ip):
            return redirect('/login?error=locked')

        user = request.form.get('username') #zabiera dane wczytany prez surowy HTML
        password = request.form.get('password')
        if user == os.environ.get('ADMIN_USER') and check_password_hash(os.environ.get('ADMIN_PASSWORD_HASH', ''), password):
            clear_failed_attempts(ip)
            session['logged_in'] = True #sets a variable in the session
            session['csrf_token'] = secrets.token_hex(16)
            resp = redirect('/')
            resp.set_cookie('csrf_token', session['csrf_token'], httponly=False, samesite='Lax')
            return resp

        register_failed_attempt(ip)
        return redirect('/login?error=invalid')
    return send_from_directory(BASE_DIR, 'login.html') #for GET, simply returns the form


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

def read_env_users():
    users = []
    result = subprocess.run(["pdbedit", "-L"], capture_output=True, text=True) #lists users: "username:uid:description"
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        username = line.split(":")[0] #take only the username
        users.append({'username': username})
    return users

def add_to_shares(l):
    KEY_MAP = {
        'guest ok': 'guest',
        'read only': 'readonly',
        'valid users': 'validUsers',
        'write list': 'writeList',
    }
    share = {}

    for i in l:
        a, b = i.strip().split("=")
        a = a.strip()
        b = b.strip()
        if b == "yes":
            b = True
        elif b == 'no':
            b = False

        a = KEY_MAP.get(a, a)
        if a in ('validUsers', 'writeList'):
            b = b.split()

        share[a] = b
    return share

def read_smb_shares():
    shares = []
    lines=[]
    start=False
    with open(SMB_CONF_PATH, "r", encoding="utf-8") as f:
        for line in f:
            i=line.strip()
            if start and i!="":
                lines.append(i)
            #[global], [Public], [Documents]... etc
            if i.startswith("[") and i.endswith("]"):
                if start:
                    shares.append(add_to_shares(lines[0:-1]))
                section=i[1:-1]
                if section != "global":
                    lines.clear()
                    lines.append('name = '+section)

                    start=True
    #taking the last section
    if start and lines:
        shares.append(add_to_shares(lines[0:-1]))

    return shares

def change_env(e):
    request_type = e.get("type")
    user = e.get("payload").get("username")
    if not isinstance(user, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", user):
        return False, "Invalid username. Only letters, digits, _ and - are allowed (max 32 chars)."

    if request_type == "add":
        password = e.get("payload").get("password")
        if (not isinstance(password, str)or not (
                1 <= len(password) <= 128) or
                "\n" in password or
                "\r" in password or
                not re.fullmatch(r"[A-Za-z0-9!@#$%^&*()_+\-=\[\]{};:'\",.<>/?\\|`~ ]+", password)
            ):
            return False, "Invalid password."
        subprocess.run(["adduser", "-D", "-H", "-s", "/sbin/nologin", user], check=False)
        subprocess.run(
            ["smbpasswd", "-a", "-s", user],
            input=f"{password}\n{password}\n",
            capture_output=True,
            text=True,
        )
        return True, None

    elif request_type == "remove":
        subprocess.run(["pdbedit", "-x", "-u", user], capture_output=True, text=True)
        subprocess.run(["deluser", user], check=False)
        subprocess.run(["delgroup", user], check=False)
        return True, None

    elif request_type == "reset": #password change
        password = e.get("payload").get("password")
        if (not isinstance(password, str) or not (
                1 <= len(password) <= 128) or
                "\n" in password or
                "\r" in password or
                not re.fullmatch(r"[A-Za-z0-9!@#$%^&*()_+\-=\[\]{};:'\",.<>/?\\|`~ ]+", password)
        ):
            return False, "Invalid password."
        subprocess.run(
            ["smbpasswd", "-s", user], #without -a because the user already exists
            input=f"{password}\n{password}\n",
            capture_output=True,
            text=True,
        )
        return True, None
    return False, "unknown action type"


def change_smb(e):
    request_type = e.get("type")

    payload = e.get("payload")
    name = payload.get("name")

    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", name):
        return False, "Invalid share name. Only letters, digits, _ and - are allowed (max 32 chars)"

    if name.lower() == 'global':
        return False, "global is forbidden share name, sorry :("

    if request_type == "add":
        payload_p = payload.get("path")
        writelist = payload.get("writeList")
        validusers = payload.get("validUsers")

        if (not isinstance(payload_p, str)
                or not payload_p.startswith("/share/")
                or ".." in payload_p.split("/")
                or not re.fullmatch(r"[A-Za-z0-9_\-./ ]+", payload_p)):
            return False, "Share path should start with /share/, must not contain '..', and may only contain letters, digits, spaces, '_', '-', '.', '/'"
        if not isinstance(writelist, list) or not all(
                isinstance(u, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,32}", u) for u in writelist):
            return False, "Invalid username added to share writelist"
        if not isinstance(validusers, list) or not all(
                isinstance(u, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,32}", u) for u in validusers):
            return False, "Invalid username added to share validusers"

        with open(SMB_CONF_PATH, "a", encoding="utf-8") as f:
            f.write(f"""


[{payload.get("name")}]
    path = {payload_p}
        
    browseable = {"yes" if payload.get("browseable") else "no"}
    guest ok = {"yes" if payload.get("guest") else "no"}
                
    read only = {"yes" if payload.get("readonly") else "no"}
    write list = {" ".join(writelist)}
                
    valid users = {" ".join(validusers)}
        
    force user = smbuser
    force group = smb
    create mask = 0660
    directory mask = 0770""")
        return True, None
    elif request_type=="remove":
        removing=False
        with open(SMB_CONF_PATH, encoding="utf-8") as f:
            kept_lines=[]
            for line in f:
                check=line.strip()
                if removing and check.startswith("["):
                    removing=False
                if check == f"[{payload.get('name')}]":
                    removing=True
                if not removing:
                    kept_lines.append(line)
        while kept_lines and kept_lines[-1].strip() == "": #after last (in order) share deleton removes remaining empty lines
            kept_lines.pop()
        with open(SMB_CONF_PATH, "w", encoding="utf-8") as f:
            f.writelines(kept_lines)
        return True, None
    return False, "Unknown action type"

@app.route('/')
@login_required
def index():
    return send_from_directory(BASE_DIR, 'Panel.html')


@app.route('/api/config', methods=['GET'])
@login_required
def get_config():
    return jsonify({
        'users': read_env_users(),
        'shares': read_smb_shares(),
    })

@app.route('/api/apply', methods=['POST'])
@login_required
@csrf_protect
def apply_changes():
    result = subprocess.run(
        ["smbcontrol", "all", "reload-config"], #all processes must read smb.conf again
        capture_output=True,
        text=True,
    )

    ok = result.returncode == 0
    return jsonify({'ok': ok, 'stdout': result.stdout, 'stderr': result.stderr}), (200 if ok else 500)

@app.route('/api/events', methods=['POST'])
@login_required
@csrf_protect
def post_event():
    event = request.get_json(force=True, silent=True) #gets HTTP json request and coverts it to dict
    if not event:
        return jsonify({'error': 'invalid json'}), 400

    entity = event.get("entity")
    if entity=="share":
        ok, error = change_smb(event)
    elif entity=="user":
        ok, error = change_env(event)
    else:
        return jsonify({'error': 'unknown entity'}), 400

    if not ok:
        return jsonify({'error': error}), 400

    return jsonify({'status': 'received', 'action': event.get('action')}), 200


if __name__ == '__main__':
    load_dotenv()
    app.run(host='0.0.0.0', port=8000, debug=False)
