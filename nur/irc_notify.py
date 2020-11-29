import socket
import ssl
from typing import List, Optional
from urllib.parse import urlparse


def notify_irc(
    server: str,
    nick: str,
    password: Optional[str],
    channel: str,
    tls: bool = True,
    port: int = 6697,
    messages: List[str] = [],
) -> None:
    if not messages:
        return

    sock = socket.socket()
    if tls:
        sock = ssl.wrap_socket(
            sock, cert_reqs=ssl.CERT_NONE, ssl_version=ssl.PROTOCOL_TLSv1_2
        )

    def _send(command: str) -> int:
        return sock.send((f"{command}\r\n").encode())

    sock.connect((server, port))
    if password:
        _send(f"PASS {password}")
    _send(f"NICK {nick}")
    _send(f"USER {nick} {server} bla :{nick}")
    _send(f"JOIN :{channel}")

    for m in messages:
        _send(f"PRIVMSG {channel} :{m}")

    _send("INFO")

    while True:
        data = sock.recv(4096)
        if not data:
            raise RuntimeError("Received empty data")

        # Assume INFO reply means we are done
        if b"End of /INFO list" in data:
            break

        if data.startswith(b"PING"):
            sock.send(data.replace(b"PING", b"PONG"))

    sock.send(b"QUIT")
    sock.close()


def send(url: str, notifications: List[str]) -> None:
    parsed = urlparse(f"http://{url}")
    username = parsed.username or "nur-bot"
    server = parsed.hostname or "chat.freenode.de"
    if parsed.path != "/" or parsed.path == "":
        channel = f"#{parsed.path[1:]}"
    else:
        channel = "#nixos-nur"
    port = parsed.port or 6697
    password = parsed.password
    if len(notifications) == 0:
        return
    notify_irc(
        server=server,
        nick=username,
        password=password,
        channel=channel,
        port=port,
        messages=notifications,
    )
