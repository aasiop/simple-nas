from flask import Flask, jsonify, request, send_from_directory, session, redirect #session przechowuje dane sesji użytkownika (słownik przypisany do użytkownika)
import os
import re
import time
import secrets
from dotenv import load_dotenv, dotenv_values, set_key, unset_key
from werkzeug.security import check_password_hash #Flash stoi na Werkzeug więc jest już pobrany
import subprocess

load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = os.environ.get('SECRET_KEY') #dane trzymane w ciasteczku

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, '.env')
SMB_CONF_PATH = '/etc/samba/smb.conf'


#ip -> (ile błędnych prób z rzędu, do kiedy zablokowany - timestamp)
failed_logins = {}
MAX_ATTEMPTS = 5
LOCK_SECONDS = 300

def is_locked(ip):
    count, locked_until = failed_logins.get(ip, (0, 0)) #pobiera ilosc nieudanych logowan, jeśli nie ma (pierwsze logowanie) to daje (0,0) = (ilosc_nieudanych, czas_czekania)
    return time.time() < locked_until #mniejszy = true, wiekszy = false

def register_failed_attempt(ip): #wywolywane po nieudanej probie
    count, _ = failed_logins.get(ip, (0, 0))
    count += 1
    if count >= MAX_ATTEMPTS:
        failed_logins[ip] = (count, time.time() + LOCK_SECONDS)
    else:
        failed_logins[ip] = (count, 0)

def clear_failed_attempts(ip):
    failed_logins.pop(ip, None) #usuwa wpis dla danego ip

def login_required(view): #decorator
    def wrapped(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect('/login') #nie zalogowany
        return view(*args, **kwargs) #zalogowany
    wrapped.__name__ = view.__name__ #Dla Flasha nie może funkcja nazywać sie wrapped tylko wymaga unikalnej nazwy funkcji dla kontkretnej trasy
    return wrapped

def csrf_protect(view): #decorator - chroni przed CSRF akcje, które coś zmieniają
    def wrapped(*args, **kwargs):
        session_token = session.get('csrf_token') #true/false
        header_token = request.headers.get('X-CSRF-Token') #true/false
        if not session_token or not header_token or not secrets.compare_digest(session_token, header_token):
            return jsonify({'error': 'bad csrf token'}), 403
        return view(*args, **kwargs)
    wrapped.__name__ = view.__name__
    return wrapped

@app.route('/login', methods=['GET', 'POST']) #GET - ktoś chce zobaczyć formularz, POST - ktoś chce się zalogować
def login():
    if request.method == 'POST':
        ip = request.remote_addr #adres IP, z którego przyszło żądanie, Flask sam to wyciąga z TCP

        if is_locked(ip):
            return redirect('/login?error=locked')

        user = request.form.get('username') #zabiera dane wczytany prez surowy HTML
        password = request.form.get('password')
        if user == os.environ.get('ADMIN_USER') and check_password_hash(os.environ.get('ADMIN_PASSWORD_HASH', ''), password):
            clear_failed_attempts(ip)
            session['logged_in'] = True #ustawiamy zmienna w session
            session['csrf_token'] = secrets.token_hex(16)
            resp = redirect('/')
            resp.set_cookie('csrf_token', session['csrf_token'], httponly=False, samesite='Lax')
            return resp

        register_failed_attempt(ip)
        return redirect('/login?error=invalid')
    return send_from_directory(BASE_DIR, 'login.html') #dla GET zwraca po prostu formularz


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

def read_env_users():
    users = []
    result = subprocess.run(["pdbedit", "-L"], capture_output=True, text=True) #komenda samby wypisuje userów: "username:uid:opis"
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        username = line.split(":")[0] #bierzemy tylko nazwe uzytkownika
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
    # obsługa ostatniej sekcji
    if start and lines:
        shares.append(add_to_shares(lines[0:-1]))

    return shares

def change_env(e):
    request_type = e.get("type")
    user = e.get("payload").get("username")

    if request_type == "add":
        password = e.get("payload").get("password")
        subprocess.run(["adduser", "-D", "-H", "-s", "/sbin/nologin", user], check=False)
        proc = subprocess.run(
            ["smbpasswd", "-a", "-s", user],
            input=f"{password}\n{password}\n",
            capture_output=True,
            text=True,
        )

    elif request_type == "remove":
        subprocess.run(["smbpasswd", "-x", user], capture_output=True, text=True)
        subprocess.run(["deluser", user], check=False)

    elif request_type == "reset": #zmiana hasla
        password = e.get("payload").get("password")
        #bez -a bo user już istnieje
        subprocess.run(
            ["smbpasswd", "-s", user],
            input=f"{password}\n{password}\n",
            capture_output=True,
            text=True,
        )


def change_smb(e):
    request_type = e.get("type")

    payload = e.get("payload")
    if payload.get('name') == 'global':
        print("global is forbidden share name, sorry :(")
    else:
        if request_type=="add":
            writelist=payload.get("writeList")
            validusers=payload.get("validUsers")
            with open(SMB_CONF_PATH, "a", encoding="utf-8") as f:
                f.write(f"""


[{payload.get("name")}]
    path = {payload.get("path")}
        
    browseable = {"yes" if payload.get("browseable") else "no"}
    guest ok = {"yes" if payload.get("guest") else "no"}
                
    read only = {"yes" if payload.get("readonly") else "no"}
    write list = {" ".join(writelist)}
                
    valid users = {" ".join(validusers)}
        
    force user = smbuser
    force group = smb
    create mask = 0660
    directory mask = 0770""")
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
            while kept_lines and kept_lines[-1].strip() == "": #after last (in order) share deleton removes last empty lines
                kept_lines.pop()
            with open(SMB_CONF_PATH, "w", encoding="utf-8") as f:
                f.writelines(kept_lines)

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
        ["smbcontrol", "all", "reload-config"], #wszystkie procesy musza znowu odczytac smb.conf
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

    if event.get("entity") == "share":
        change_smb(event)
    elif event.get("entity") == "user":
        change_env(event)
    else:
        print("html broken")

    return jsonify({'status': 'received', 'action': event.get('action')}), 200


if __name__ == '__main__':
    load_dotenv()
    app.run(host='0.0.0.0', port=8000, debug=False)
