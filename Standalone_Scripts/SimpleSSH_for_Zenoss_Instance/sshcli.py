#!/usr/bin/env python3

from twisted.conch import error
from twisted.conch.ssh import transport, connection, keys, userauth, channel, common
from twisted.internet import defer, protocol, reactor
import sys
import getpass

class ClientCommandTransport(transport.SSHClientTransport):
    def __init__(self, username: str, password: str, command: str):
        super().__init__()
        self.username = username
        self.password = password
        self.command = command

    def verifyHostKey(self, pubKey: bytes, fingerprint: str) -> defer.Deferred:
        # In a real app, you should verify that the fingerprint matches
        # the one you expected to get from this server
        return defer.succeed(True)

    def connectionSecure(self):
        self.requestService(
            PasswordAuth(self.username, self.password,
                         ClientConnection(self.command)))

class PasswordAuth(userauth.SSHUserAuthClient):
    def __init__(self, user: str, password: str, connection: protocol.Protocol):
        super().__init__(user, connection)
        self.password = password

    def getPassword(self, prompt: str = None) -> defer.Deferred:
        return defer.succeed(self.password)

class ClientConnection(connection.SSHConnection):
    def __init__(self, cmd: str):
        super().__init__()
        self.command = cmd

    def serviceStarted(self):
        self.openChannel(CommandChannel(self.command, conn=self))

class CommandChannel(channel.SSHChannel):
    name = 'session'

    def __init__(self, command: str, **kwargs):
        super().__init__(**kwargs)
        self.command = command

    def channelOpen(self, data: bytes):
        self.conn.sendRequest(
            self, 'exec', common.NS(self.command), wantReply=True).addCallback(
            self._gotResponse)

    def _gotResponse(self, _):
        self.conn.sendEOF(self)

    def dataReceived(self, data: bytes):
        print(data.decode())

    def closed(self):
        reactor.stop()

class ClientCommandFactory(protocol.ClientFactory):
    def __init__(self, username: str, password: str, command: str):
        self.username = username
        self.password = password
        self.command = command

    def buildProtocol(self, addr):
        return ClientCommandTransport(
            self.username, self.password, self.command)

if __name__ == "__main__":
    try:
        server = sys.argv[1]
        command = sys.argv[2]
        username = input("Username: ")
        password = getpass.getpass("Password: ")
        factory = ClientCommandFactory(username, password, command)
        reactor.connectTCP(server, 22, factory)
        reactor.run()
    except IndexError:
        print("Usage: script.py <server> <command>")
    except Exception as e:
        print(f"An error occurred: {e}")
