from flask import Flask, jsonify, request, send_from_directory
import os
import re
import configparser
from dotenv import load_dotenv, dotenv_values, set_key, unset_key

app = Flask(__name__, static_folder='.', static_url_path='')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, '.env')
SMB_CONF_PATH = os.path.join(BASE_DIR, 'smb.conf')

usernames=[]


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
    with open("smb.conf") as f:
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

def change_smb(e):
    print()

@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'Panel.html')


@app.route('/api/config', methods=['GET'])
def get_config():
    """Zwraca aktualny stan configu (odczytany z .env i smb.conf) do wyświetlenia w panelu."""
    return jsonify({
        'users': read_env_users(),
        'shares': read_smb_shares(),
    })


@app.route('/api/events', methods=['POST'])
def post_event():
    """Odbiera event zmiany configu z panelu."""
    event = request.get_json(force=True, silent=True) #gets HTTP json request and coverts it to dict
    if not event:
        return jsonify({'error': 'invalid json'}), 400

    print(event)
    if event.get("entity") == "share":
        change_smb(event)
    elif event.get("entity") == "user":
        change_env(event)
    else:
        print("html broken")

    return jsonify({'status': 'received', 'action': event.get('action')}), 200


if __name__ == '__main__':
    load_dotenv()
    app.run(host='0.0.0.0', port=8000, debug=True)
