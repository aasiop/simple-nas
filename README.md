Simple lightweight NAS file server based on Samba running inside a Docker container. Works on any system capable of running Docker

The container uses the `dperson/samba` image and exposes a selected host directory as a network share.

## Requirements
- Docker
- Docker Compose
- Administrator privileges (`sudo`)
- A directory for storing NAS data

# Installation:
Install Docker
```
curl -fsSL https://get.docker.com | sudo sh
```

(optional) Allow Docker usage without sudo
```
sudo usermod -aG docker $USER
```

Verify installation
```
docker --version
```

Clone repository
```
git clone https://github.com/aasiop/simple-nas.git
```

Enter repository
```
cd simple-nas
```

## Configure compose.yaml
`nano compose.yaml`  


```
services:
  sambanas:
    container_name: {server_name}
    image: dperson/samba
    restart: unless-stopped

    ports:
      - "445:445"

    volumes:
      - /{path}:/share

    environment:
      USERID: "1000"
      GROUPID: "1000"

    command: '-p -n -u "{login};{password}" -s "NAS;/share;yes;no;no;nas"'
```

# Configuration info:
Replace:

| Variable | Description |
|----------|-------------|
| `{server_name}` | Docker container name |
| `{path}` | NAS data directory on the host system |
| `{login}` | Samba username |
| `{password}` | Samba password |

restart:
- `unless-stopped` - automatically restarts unless manually stopped
- `always` - always restarts the container
- `on-failure` - restarts when the container exits with an error
- `no` - no automatic restart

The share format is:  
NAME;PATH;VISIBLE;WRITABLE;GUEST;USER  
"NAS;/share;yes;no;no;nas":

- `/share` - directory inside the container
- `yes` - share is enabled
- `no` - read-only mode disabled (write access enabled)
- `no` - guest access disabled
- `nas` - user allowed to access the data



# Start the container
`docker compose up -d`

# Accessing the NAS share:
From Windows Explorer type:
\\SERVER_IP\NAS

Example:
`\\192.168.1.50\NAS`

Then use login and password

Done!