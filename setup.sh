#!/bin/sh
set -e

#Nie nadpisuj czegoś, co już istnieje, bez pytania
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

#Pytamy o nazwe serwera a jak nie zostanie wpisana to będzie to home-nas
printf "Server name: "
read -r SERVER_NAME
SERVER_NAME=${SERVER_NAME:-home-nas}

printf "Host path (folder on your machine to share) [example: /mnt/storage]: "
read -r HOST_PATH
HOST_PATH=${HOST_PATH:-/mnt/storage}

printf "Admin user login: "
read -r ADMIN_USER
ADMIN_USER=${ADMIN_USER:-admin}

#To samo ale nie widać wpisywanego hasła
printf "Admin password: "
stty -echo
read -r ADMIN_PASSWORD
stty echo
echo

USER_ID=$(id -u)
GROUP_ID=$(id -g)

SECRET_KEY=$(openssl rand -hex 32)

#Tworzy kontener i instaluje tam pakiet oraz tworzy hash hasła po czym się usuwa
echo "Generating password hash (pulling a small python image, once)..."
ADMIN_PASSWORD_HASH=$(docker run --rm -e PW="$ADMIN_PASSWORD" python:3-alpine sh -c \
    'pip install -q --root-user-action=ignore werkzeug && python3 -c \
    "import os; from werkzeug.security import generate_password_hash as g; print(g(os.environ[\"PW\"]))"')


cat > .env << EOF
SERVER_NAME=${SERVER_NAME}
HOST_PATH=${HOST_PATH}
USER_ID=${USER_ID}
GROUP_ID=${GROUP_ID}
SECRET_KEY='${SECRET_KEY}'
ADMIN_USER=${ADMIN_USER}
ADMIN_PASSWORD_HASH='${ADMIN_PASSWORD_HASH}'
EOF

cat > smb.conf << EOF
[global]
    workgroup = WORKGROUP
    security = user

    server string = ${SERVER_NAME}
    netbios name = ${SERVER_NAME}

    map to guest = never

    server min protocol = SMB2

    load printers = no
    printing = bsd
    printcap name = /dev/null

    log level = 1
EOF