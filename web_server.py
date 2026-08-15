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
SMB_CONF_PATH = os.path.join(BASE_DIR, 'smb.conf')

usernames=[]

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
    global usernames
    usernames.clear()
    users.clear()
    config = dotenv_values(".env")
    users_count=0

    for key in config:
        if key.startswith("USER_"):
            users_count+=1
    users_count-=1 #USER_ID is not a user

    for i in range(1, users_count+1):
        user = "USER_"+ str(i)
        password = "PASSWORD_"+ str(i)
        users.append({'username': config.get(user), 'password': config.get(password)})
        usernames.append(config.get(user)) #for change_env

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
    with open("smb.conf", "r", encoding="utf-8") as f:
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
    global usernames

    request_type = e.get("type")
    c = len(usernames)

    if request_type == "add":
        user = e.get("payload").get("username")
        if user not in usernames:
            user_index = "USER_" + str(c + 1)
            password_index = "PASSWORD_" + str(c + 1)
            password = e.get("payload").get("password")
            set_key(".env", user_index, user, quote_mode="never")
            set_key(".env", password_index, password, quote_mode="never")
        else:
            print(f'User named "{user}" already exists!')

    elif request_type == "remove":
        value = e.get("payload").get("username")
        config = dotenv_values(".env")
        #find index
        for i in range(1, c+1):
            del_index="USER_" + str(i)
            if config.get(del_index) == value:
                for j in range(i+1, c+1): #We move all indexes down excluding the one we delete
                    next_user = config.get("USER_" + str(j))
                    next_pass = config.get("PASSWORD_" + str(j))

                    if next_user:
                        set_key(".env", "USER_" + str(j-1), next_user, quote_mode="never")
                    if next_pass:
                        set_key(".env", "PASSWORD_" + str(j-1), next_pass, quote_mode="never")

                #Delete last unused index
                unset_key(".env", "USER_" + str(c))
                unset_key(".env", "PASSWORD_" + str(c))
                break
    sync_compose_users()

def change_smb(e):
    request_type = e.get("type")

    payload = e.get("payload")
    if payload.get('name') == 'global':
        print("global is forbidden share name, sorry :(")
    else:
        if request_type=="add":
            writelist=payload.get("writeList")
            validusers=payload.get("validUsers")
            with open("smb.conf", "a", encoding="utf-8") as f:
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
            with open("smb.conf", encoding="utf-8") as f:
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
            with open("smb.conf", "w", encoding="utf-8") as f:
                f.writelines(kept_lines)

def sync_compose_users():
    config = dotenv_values(".env")
    users_count = sum(1 for key in config if key.startswith("USER_")) - 1

    with open("compose.yaml", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    skip_blank = False

    for line in lines:
        stripped = line.strip()

        if re.match(r'^USER\d*:', stripped):
            continue

        if skip_blank and stripped == "":
            skip_blank = False
            continue

        new_lines.append(line)
        skip_blank = False

        if stripped.startswith("GROUPID:"):
            indent = line[:len(line) - len(line.lstrip())]
            if users_count > 0:
                new_lines.append("\n")
                for i in range(1, users_count + 1):
                    key = "USER" if i == 1 else f"USER{i}"
                    new_lines.append(f'{indent}{key}: "${{USER_{i}}};${{PASSWORD_{i}}}"\n')
            skip_blank = True

    with open("compose.yaml", "w", encoding="utf-8") as f:
        f.writelines(new_lines)

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
    try:
        result = subprocess.run(
            ["docker", "compose", "up", "-d", "--force-recreate", "sambanas"],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        return jsonify({'ok': False, 'error': 'docker command not found'}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'ok': False, 'error': 'command timed out after 60s'}), 500

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
