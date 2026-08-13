# Simple NAS

Simple lightweight NAS file server based on Samba running inside a Docker container. Works on any system capable of running Docker

The container uses the `dperson/samba` image and exposes selected host directories as network shares.

There is now available web configuration.

## Features

- Docker-based deployment
- Persistent storage
- Multi-user support
- Multiple shares
- Web panel
- Lightweight

## Requirements
- Docker
- Docker Compose
- Flask and dotenv python libraries

---

## Installation:

Clone the repository:  
```bash
git clone https://github.com/aasiop/simple-nas.git
```

Enter repository:  
```bash
cd simple-nas
```

Edit server configuration:  
```bash
cp .env.example .env
```

Change permissions 
```bash
chmod 600 .env
```

Edit docker configuration:  
```bash
nano .env
```

Start the container:
```bash
docker compose up -d
```

Verify that the container is running:
```bash
docker ps
```

---

## Configuration

Create a `.env` file from `.env.example`.

Example:
```env
SERVER_NAME=home-nas
HOST_PATH=/mnt/storage

USER_ID=1000
GROUP_ID=1000

...
```

| Variable | Description                    |
|----------|--------------------------------|
| `SERVER_NAME` | Docker container name          |
| `HOST_PATH` | Directory on the host to share |
| `USER_ID` | Linux user ID                  |
| `GROUP_ID` | Linux group ID                 |

---
## Web panel configuration:
> WARNING web configuration don't require password. It's still in development! Close it after making changes!

Turn on panel:
```bash
python3 web_server.py
```

Open your web browser on host and type:
```text
http://localhost:8000/
```

Or on another machine in the same network:
```text
http://SERVER_IP:8000/
```

## Accessing the Share:

### Windows
Open File Explorer and enter:
```text
\\SERVER_IP\SHARE_NAME
```

Example:
```text
\\192.168.1.50\SHARE_NAME
```

Then enter the configured Samba username and password.

### Linux
Open your file manager and connect to:
```text
smb://SERVER_IP/SHARE_NAME
```

or mount it manually:
```bash
sudo mount -t cifs //SERVER_IP/SHARE_NAME /mnt/SHARE_NAME
```

### Debug
If Windows system cannot find shared folder try using:
```cmd
net use * /delete
```
Warning: This will disconnect all active SMB network connections.

## License
This project is licensed under the MIT License.

