# LiteNAS

Turn any Docker-capable machine into your own simple home file server. LiteNAS lets you share folders over your local network using SMB/Samba and manage your server through a lightweight web interface.

Instead of installing a complete NAS operating system just to share a few drives or folders, you can run LiteNAS alongside the rest of your services and keep your setup under your control.

LiteNAS keeps things focused on what you actually need: file sharing, a small web configuration panel, and Docker-based deployment.

---

- Login panel

![Login](./screenshots/login.png)

- Configuration panel

![Configuration panel](./screenshots/panel.png)

---

## Features

- Docker-based deployment
- Persistent storage
- Multi-user support
- Multiple shares
- Web configuration panel
- Lightweight

---

## Requirements
- Docker
- Docker Compose
- Python 3.9+
- OpenSSL
- Internet connection for initial setup

---

## Installation

Clone the repository:  
```bash
git clone https://github.com/aasiop/LiteNAS.git
```

Enter repository:  
```bash
cd LiteNAS
```

Run the setup script. It will interactively ask for the server name, host directory and website administrator credentials, then generate the .env and smb.conf files automatically.  
```bash
sh setup.sh
```

Start the container:
```bash
docker compose up -d
```

Verify that the container is running:
```bash
docker ps
```

After starting the container, open the web configuration panel to configure users and shares.

---

## Security
- Do not expose port 8000 directly to the Internet.
- Do not expose SMB/445 to the Internet.
- Use the web panel only inside a trusted network or behind a properly configured reverse proxy/VPN.
- Use strong administrator credentials.

---

## Configuration

To enter NAS share configuration, type:
```text
http://localhost:8000/
```

Or on another machine in the same network:
```text
http://SERVER_IP:8000/
```

---

## Accessing the Shares

### Windows
Open File Explorer and enter:
```text
\\SERVER_IP\SHARE_NAME
```

Example:
```text
\\192.168.1.50\home-nas
```

Then enter the configured user credentials

### Linux
Open your file manager and connect to:
```text
smb://SERVER_IP/SHARE_NAME
```

or mount it manually:
```bash
sudo mount -t cifs //SERVER_IP/SHARE_NAME /mnt/SHARE_NAME
```

---

## Debug
If Windows cannot find the shared folder, try:
```cmd
net use * /delete
```
Warning: This will disconnect all active SMB network connections.

---

If port 8000 is already in use, you can change the web panel port:

in `web_server.py` port 8000 (last line):
```text
app.run(host='0.0.0.0', port=8000, debug=False)
```

in `Dockerfile` replace 8000 with new port number (do not change 445!):
```text
EXPOSE 445 8000
```

in `compose.yaml` replace port 8000:8000 with new port numer (do not change 445:445!):
```text
ports:
  - "445:445"
  - "8000:8000"
```

---

If you encounter any problems with .env file configuration see example:
```env
SERVER_NAME=home-nas
HOST_PATH=/mnt/storage

USER_ID=1000
GROUP_ID=1000

SECRET_KEY=REPLACE_ME_generate_with_secrets
ADMIN_USER=admin
ADMIN_PASSWORD_HASH=REPLACE_ME_generate_with_werkzeug
```

| Variable              | Description                          |
|-----------------------|--------------------------------------|
| `SERVER_NAME`         | Docker container name                |
| `HOST_PATH`           | Directory on the host to share       |
| `USER_ID`             | Linux user ID                        |
| `GROUP_ID`            | Linux group ID                       |
| `SECRET_KEY`          | Random string for session management |
| `ADMIN_USER`          | Login name of admin user             |
| `ADMIN_PASSWORD_HASH` | Password hash                        |

Use these commands for:
- secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```
- admin password:
```bash
python3 -c "from werkzeug.security import generate_password_hash as g; print(g('your password'))"
```

---

## License
This project is licensed under the MIT License.