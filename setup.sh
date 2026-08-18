#!/bin/sh
set -e

# Nie nadpisuj czegoś, co już istnieje, bez pytania - .env może mieć
# prawdziwe SECRET_KEY/ADMIN_PASSWORD_HASH, które nie chcemy stracić.
for f in .env smb.conf; do
    if [ -f "$f" ]; then
        printf "%s already exists. Overwrite? [y/N] " "$f"
        read -r answer
        case "$answer" in
            y|Y) ;;
            *) echo "Aborted - $f left untouched."; exit 1 ;;
        esac
    fi
done

printf "Server name: "
read -r SERVER_NAME
SERVER_NAME=${SERVER_NAME:-home-nas}

printf "Host path (folder on your machine to share) [example: /mnt/storage]: "
read -r HOST_PATH
HOST_PATH=${HOST_PATH:-/mnt/storage}

cat > .env << EOF
SERVER_NAME=${SERVER_NAME}
HOST_PATH=${HOST_PATH}
USER_ID=1000
GROUP_ID=1000
SECRET_KEY=REPLACE_ME_generate_with_secrets
ADMIN_USER=admin
ADMIN_PASSWORD_HASH=REPLACE_ME_generate_with_werkzeug
EOF

cat > smb.conf << 'EOF'
[global]
    workgroup = WORKGROUP
    security = user

    server string = home-nas
    netbios name = home-nas

    map to guest = never

    server min protocol = SMB2

    load printers = no
    printing = bsd
    printcap name = /dev/null

    log level = 1
EOF

echo "Created .env and smb.conf."
echo "Remember to fill in SECRET_KEY and ADMIN_PASSWORD_HASH in .env before running the container."