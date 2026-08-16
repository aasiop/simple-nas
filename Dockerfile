FROM dperson/samba

RUN apk add --no-cache python3 py3-pip # na tym stoi obraz

COPY requirements.txt /app/requirements.txt # dajemy w apke, żeby na nowo nie instalować wszystkich pakietów
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY web_server.py Panel.html login.html /app/
WORKDIR /app

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 445 8000
ENTRYPOINT ["/entrypoint.sh"]