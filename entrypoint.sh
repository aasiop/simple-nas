#!/bin/sh
set -e #w przypadku awarii skrypt zwroci błąd zamiast starać się ciągnąć dalej

for u in $(pdbedit -L 2>/dev/null | cut -d: -f1); do
    if ! id "$u" >/dev/null 2>&1; then
        adduser -D -H -s /sbin/nologin "$u"
    fi
done

#$ to proces w tle
#$! pokazuje PID
/usr/bin/samba.sh -p &
SAMBA_PID=$!

#uruchamia panel w tle
python3 /app/web_server.py &
PANEL_PID=$!

#gdy kontener dostanie sygnał zamknięcia, ten skrypt dostanie go pierwszy. Pozwala na grzeczne zamknięcie
trap 'kill -TERM "$SAMBA_PID" "$PANEL_PID" 2>/dev/null' TERM INT

#czekaj, aż pierwszy z dwóch procesów się zakończy dopiero potem drugi
wait -n "$SAMBA_PID" "$PANEL_PID"
