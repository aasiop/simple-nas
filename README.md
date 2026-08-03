Simple lightweight NAS file server based on Samba running inside a Docker container. Works on any system capable of running Docker

The container uses the `dperson/samba` image and exposes a selected host directory as a network share.

# Requirements
- Docker
- Docker Compose
- Administrator privileges (`sudo`)
- A directory for storing NAS data

1. Installation:
# Install Docker
curl -fsSL https://get.docker.com | sudo sh

# (optional) Allow Docker usage without sudo
sudo usermod -aG docker $USER

# Verify installation
docker --version

# Clone repository
git clone https://github.com/aasiop/REPOSITORY.git

# Enter repository
cd REPOSITORY

# Configure compose.yaml
nano compose.yaml


~
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
~

# Configuration info:
Replace:
{server_name} - Docker container name
{path}        - NAS data directory on the host system
{login}       - Samba username
{password}    - Samba password

restart:
unless-stopped	- only manual stop
always		- self explainatory
on-failure	- restarts when container exits with an error
no		- no automatic restart

"NAS;/share;yes;no;no;nas":
/share 	- directory inside container
yes	- share is enabled
no	- write only
no	- guest only
nas	- witch user is allowed to access data



# Start the container
docker compose up -d

2. Accessing the NAS share:
# From Windows explorator type:
\\SERVER_IP\NAS

# Use login and password

Done !