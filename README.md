# Simple NAS

Simple lightweight NAS file server based on Samba running inside a Docker container. Works on any system capable of running Docker

The container uses the `dperson/samba` image and exposes a selected host directory as a network share.

## Features

- Docker-based deployment
- Persistent storage
- Easy configuration
- Lightweight

## Requirements
- Docker
- Docker Compose

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

Create your configuration file:  
```bash
cp .env.example .env
```

Edit the configuration:  
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
SERVER_NAME     = home-nas
HOST_PATH       = /mnt/storage
SAMBA_USER      = nas
SAMBA_PASSWORD  = StrongPassword123
USER_ID         = 1000
GROUP_ID        = 1000
```

| Variable | Description |
|----------|-------------|
| `SERVER_NAME` | Docker container name |
| `HOST_PATH` | Directory on the host to share |
| `SAMBA_USER` | Samba username |
| `SAMBA_PASSWORD` | Samba password |
| `USER_ID` | Linux user ID |
| `GROUP_ID` | Linux group ID |

---

## compose.yaml configuration

```yaml
services:
  sambanas:
    container_name: ${SERVER_NAME}
    image: dperson/samba
    restart: unless-stopped

    ports:
      - "445:445"

    volumes:
      - ${HOST_PATH}:/share

    environment:
      USERID: "${USER_ID}"
      GROUPID: "${GROUP_ID}"

    command: '-p -n -u "${SAMBA_USER};${SAMBA_PASSWORD}" -s "NAS;/share;yes;no;no;${SAMBA_USER}"'

```


### Restart Policy
| Policy | Description |
|--------|-------------|
| `unless-stopped` | Restart unless manually stopped |
| `always` | Always restart |
| `on-failure` | Restart only after errors |
| `no` | Disable automatic restart |

### Share configuration
The `-s` option follows the format:
```text
NAME;PATH;VISIBLE;WRITABLE;GUEST;USER
```

Current configuration:
```text
NAS;/share;yes;no;no;${SAMBA_USER}
```
| Value | Description |
|-------|-------------|
| `NAS` | Share name visible on the network |
| `/share` | Directory inside the container |
| `yes` | Share is visible |
| `no` | Guest write access disabled |
| `no` | Guest login disabled |
| `${SAMBA_USER}` | User allowed to access the share |

## Accessing the Share:

### Windows
Open File Explorer and enter:
```text
\\SERVER_IP\NAS
```

Example:
```text
\\192.168.1.50\NAS
```

Then enter the configured Samba username and password.

### Linux
Open your file manager and connect to:
```text
smb://SERVER_IP/NAS
```

or mount it manually:
```bash
sudo mount -t cifs //SERVER_IP/NAS /mnt/nas
```

## License
This project is licensed under the MIT License.

