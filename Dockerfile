FROM dperson/samba

#Install Python and pip without keeping the package cache
RUN apk add --no-cache python3 py3-pip

#Copy files to container
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY web_server.py Panel.html login.html /app/
WORKDIR /app

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

#Run the entrypoint script when the container starts
EXPOSE 445 8000
ENTRYPOINT ["/entrypoint.sh"]