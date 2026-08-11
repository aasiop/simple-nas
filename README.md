# Simple NAS

Simple lightweight NAS file server based on Samba running inside a Docker container. Works on any system capable of running Docker

The container uses the `dperson/samba` image and exposes selected host directories as network shares.

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

---

## Installation:

> This project is currently under development. Manual installation is required.

Clone the repository:  
```bash
git clone https://github.com/aasiop/simple-nas.git
```

Enter repository:  
```bash
cd simple-nas
```

Edit server and users configuration:  
```bash
nano .env
```

Edit container configuration:  
```bash
nano compose.yaml
```

Edit shares configuration:  
```bash
nano smb.conf
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

USER_1=alice
PASSWORD_1=alice1

USER_2=bob
PASSWORD_2=bob1

...
```

| Variable | Description                    |
|----------|--------------------------------|
| `SERVER_NAME` | Docker container name          |
| `HOST_PATH` | Directory on the host to share |
| `USER_ID` | Linux user ID                  |
| `GROUP_ID` | Linux group ID                 |
| `USER_1` | Samba username                 |
| `PASSWORD_1` | Samba password                 |

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
      - ./smb.conf:/etc/samba/smb.conf:ro

    environment:
      USERID: "${USER_ID}"
      GROUPID: "${GROUP_ID}"

      USER: "${USER_1};${PASSWORD_1}"
      USER2: "${USER_2};${PASSWORD_2}"
      #USER3: ...

    command: '-p'
```


#### Restart Policy
| Policy | Description |
|--------|-------------|
| `unless-stopped` | Restart unless manually stopped |
| `always` | Always restart |
| `on-failure` | Restart only after errors |
| `no` | Disable automatic restart |

#### adding users
add another line for another user:
```yaml
USER3: "${USER_3};${PASSWORD_3}"
```

## adding shares

Shares are configured in `smb.conf`, example:

```text
[Public]
    path = /share/public

    browseable = yes
    guest ok = no

    read only = no
    write list = alice bob

    valid users = alice bob

    force user = smbuser
    force group = smb
    create mask = 0660
    directory mask = 0770


[Documents]
    path = /share/documents

    browseable = yes

    ...
```
| Policy | Description                                             |
|--------|---------------------------------------------------------|
| `[Public]` | Network share name                                      |
| `path` | Subdirectory to share                                   |
| `browseable` | Whether the share is visible when browsing the server   |
| `guest ok` | Whether guest access is allowed                         |
| `read only` | Whether the share is read-only                          |
| `write list` | Users allowed to write to the share (even if read only) |
| `valid users` | Users allowed to access the share                                                       |


## Web panel and configuration (under development):

Open your web browser and type:
```text
http://localhost:8000/
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

