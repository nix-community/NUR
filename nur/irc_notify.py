import ssl
from typing import List, Optional
from urllib.parse import urlparse

from irc.client import Connection, Event, Reactor, ServerConnectionError, is_channel
from irc.connection import Factory


class Exit(SystemExit):
    pass


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
    _send(
        notifications=notifications,
        nickname=username,
        password=password,
        server=server,
        channel=channel,
        port=port,
    )


class _send:
    def __init__(
        self,
        notifications: List[str],
        server: str,
        nickname: str,
        port: int,
        channel: str,
        password: Optional[str] = None,
        use_ssl: bool = True,
    ) -> None:
        self.notifications = notifications
        self.channel = channel

        ssl_factory = None
        if use_ssl:
            ssl_factory = Factory(wrapper=ssl.wrap_socket)
        reactor = Reactor()
        try:
            s = reactor.server()
            c = s.connect(
                server, port, nickname, password=password, connect_factory=ssl_factory
            )
        except ServerConnectionError as e:
            print(f"error sending irc notification {e}")
            return

        c.add_global_handler("welcome", self.on_connect)
        c.add_global_handler("join", self.on_join)
        c.add_global_handler("disconnect", self.on_disconnect)

        try:
            reactor.process_forever()
        except Exit:
            pass

    def on_connect(self, connection: Connection, event: Event) -> None:
        if is_channel(self.channel):
            connection.join(self.channel)
            return
        self.main_loop(connection)

    def on_join(self, connection: Connection, event: Event) -> None:
        self.main_loop(connection)

    def on_disconnect(self, connection: Connection, event: Event) -> None:
        raise Exit()

    def main_loop(self, connection: Connection) -> None:
        for notification in self.notifications:
            connection.privmsg(self.channel, notification)
        connection.quit("Bye")
