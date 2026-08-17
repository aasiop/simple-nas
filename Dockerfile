FROM dperson/samba

# na tym stoi obraz
RUN apk add --no-cache python3 py3-pip

# dajemy w apke, żeby na nowo nie instalować wszystkich pakietów
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY web_server.py Panel.html login.html /app/
WORKDIR /app

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 445 8000
ENTRYPOINT ["/entrypoint.sh"]