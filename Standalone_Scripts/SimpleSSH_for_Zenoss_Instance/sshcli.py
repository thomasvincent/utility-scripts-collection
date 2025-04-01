#!/usr/bin/env python3
"""
Twisted SSH client to execute a remote command using password authentication.

This script connects to an SSH server, authenticates using a username and password,
executes a single command, prints the command's output (stdout), and exits.
"""

import argparse
import getpass
import sys
from typing import Optional, Any

# Import Twisted components
from twisted.conch.ssh import (
    transport, connection, userauth, channel, common, keys
)
from twisted.internet import defer, protocol, reactor, error as net_error
from twisted.python import failure, log # Added for logging

# --- Configuration (Conceptually part of the Application Layer) ---

class SSHClientConfig:
    """Configuration holder for SSH client parameters."""
    def __init__(self, server: str, port: int, username: str, password: str, command: str, insecure: bool):
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.command = command
        self.insecure_host_key = insecure # Flag for host key verification policy

# --- Domain Logic / Service Layer (Interacting with Twisted Protocols) ---

class ExecutingCommandChannel(channel.SSHChannel):
    """
    An SSHChannel specifically for executing a single command via 'exec'.

    Handles sending the command, receiving output, and signaling completion.
    """
    name = b'session'  # Channel type identifier (bytes)

    def __init__(self, command: str, completion_deferred: defer.Deferred, **kwargs):
        """
        Initialize the channel.

        Args:
            command: The command string to execute.
            completion_deferred: Deferred to fire upon command completion or channel close.
            **kwargs: Passthrough arguments for SSHChannel.
        """
        super().__init__(**kwargs)
        self._command = command.encode('utf-8') # Encode command for transport
        self._completion_deferred = completion_deferred
        self._output_buffer = bytearray()
        log.msg(f"CommandChannel initialized for command: {command}")

    def channelOpen(self, specific_data: bytes):
        """Called when the channel is successfully opened."""
        log.msg("Channel opened. Sending exec request.")
        # Request command execution on the remote side
        request_deferred = self.conn.sendRequest(
            self,
            b'exec', # Request type
            common.NS(self._command), # Command payload (needs Name-String formatting)
            wantReply=True
        )
        request_deferred.addCallbacks(self._exec_request_success, self._exec_request_failure)

    def _exec_request_success(self, result: Any):
        """Callback for successful 'exec' request acknowledgment."""
        # The server acknowledged the request. We can now close our write-side.
        log.msg("Exec request acknowledged by server. Sending EOF.")
        self.conn.sendEOF(self) # Signal no more data will be sent from client for command stdin

    def _exec_request_failure(self, reason: failure.Failure):
        """Errback if the 'exec' request itself fails."""
        log.err(reason, "Exec request failed")
        # Signal failure upstream
        if not self._completion_deferred.called:
            self._completion_deferred.errback(reason)
        # Close the channel as the command couldn't be initiated
        self.loseConnection()

    def dataReceived(self, data: bytes):
        """Called when data (stdout/stderr from command) is received."""
        # Simple printing; a more robust implementation might buffer/process differently
        try:
            decoded_data = data.decode('utf-8', errors='replace')
            print(decoded_data, end='', flush=True) # Print immediately
            self._output_buffer.extend(data) # Also buffer if needed later
        except Exception as e:
            log.err(e, f"Error decoding received data: {data!r}")

    def extReceived(self, dataType: int, data: bytes):
        """Called when extended data (like stderr) is received."""
        if dataType == common.EXTENDED_DATA_STDERR:
            try:
                # Treat stderr similarly to stdout for this example
                decoded_data = data.decode('utf-8', errors='replace')
                print(f"[STDERR] {decoded_data}", end='', file=sys.stderr, flush=True)
                # Optionally buffer stderr separately if needed
            except Exception as e:
                log.err(e, f"Error decoding received stderr data: {data!r}")
        else:
            log.msg(f"Received unknown extended data type {dataType}: {data!r}")

    def request_exit_status(self, data: bytes):
        """Handle the 'exit-status' request from the server."""
        exit_status = common.getNS(data)[0] # Decode exit status
        log.msg(f"Remote command exited with status: {exit_status}")
        # You might want to signal this status via the deferred
        # For now, just logging it. If status != 0, maybe errback?
        if exit_status != 0 and not self._completion_deferred.called:
             # Treat non-zero exit as an error condition
             err = failure.Failure(Exception(f"Remote command failed with exit status {exit_status}"))
             self._completion_deferred.errback(err)


    def closed(self):
        """Called when the channel is closed from either side."""
        log.msg("Channel closed.")
        # Signal completion (if not already signaled by an error or exit status)
        # Ensure the deferred is only called once.
        if not self._completion_deferred.called:
            # Assuming successful completion if closed without prior error/non-zero exit
            self._completion_deferred.callback(self._output_buffer.decode('utf-8', errors='replace'))


class ClientCommandConnection(connection.SSHConnection):
    """Represents the SSH connection itself after transport security."""
    def __init__(self, command: str, completion_deferred: defer.Deferred):
        """
        Initialize the connection service.

        Args:
            command: The command string to execute.
            completion_deferred: Deferred to signal overall command completion/failure.
        """
        super().__init__()
        self._command = command
        self._completion_deferred = completion_deferred
        log.msg("ClientConnection initialized.")

    def serviceStarted(self):
        """Called when the connection service is active."""
        log.msg("SSH Connection service started. Opening command channel.")
        # Open the channel responsible for executing the command
        self.openChannel(ExecutingCommandChannel(self._command, self._completion_deferred, conn=self))

    def serviceStopped(self):
        """Called when the connection service stops."""
        log.msg("SSH Connection service stopped.")
        # If the service stops unexpectedly before the command completes, signal error.
        if not self._completion_deferred.called:
             err = failure.Failure(Exception("SSH connection service stopped prematurely."))
             self._completion_deferred.errback(err)


class ClientPasswordAuth(userauth.SSHUserAuthClient):
    """Handles password-based SSH user authentication."""
    def __init__(self, username: str, password: str, connection_service: connection.SSHConnection):
        """
        Initialize password authentication helper.

        Args:
            username: The username for authentication.
            password: The password for authentication.
            connection_service: The SSHConnection service to start upon successful auth.
        """
        super().__init__(username.encode('utf-8'), connection_service)
        self._password = password.encode('utf-8')
        log.msg(f"PasswordAuth initialized for user: {username}")

    def getPassword(self, prompt: Optional[bytes] = None) -> defer.Deferred:
        """Provides the password when requested by the server."""
        log.msg("Password requested by server, providing stored password.")
        # Return the password immediately using a Deferred
        return defer.succeed(self._password)

    # You might also want to implement getGenericAnswers, getPublicKey, etc.,
    # if the server requires different auth steps, but for simple password auth,
    # getPassword is often sufficient.


class SecureClientTransport(transport.SSHClientTransport):
    """
    The main SSH transport layer handling the connection and host key verification.
    """
    def __init__(self, config: SSHClientConfig, connection_service: connection.SSHConnection):
        """
        Initialize the client transport.

        Args:
            config: SSH client configuration object.
            connection_service: The SSHConnection service instance.
        """
        # Note: SSHClientTransport doesn't take arguments in __init__ in recent Twisted
        # We store config locally for use in methods.
        # super().__init__() # Not needed and breaks in newer Twisted versions
        self._config = config
        self._connection_service = connection_service
        log.msg(f"ClientTransport initialized for {config.server}:{config.port}")


    def verifyHostKey(self, pubKey: bytes, fingerprint: str) -> defer.Deferred:
        """
        Verifies the server's host key.

        Args:
            pubKey: The public key blob received from the server.
            fingerprint: The fingerprint of the public key.

        Returns:
            Deferred firing True if the key is trusted, False or Failure otherwise.
        """
        log.msg(f"Verifying host key: {fingerprint}")

        if self._config.insecure_host_key:
            log.msg("WARNING: Host key verification disabled (--insecure). Accepting key.")
            return defer.succeed(True)
        else:
            # --- Production Host Key Verification Placeholder ---
            # In a real application, implement proper host key checking:
            # 1. Load known_hosts file (~/.ssh/known_hosts).
            # 2. Check if the server's hostname/IP and pubKey match an entry.
            # 3. If matched and valid -> return defer.succeed(True)
            # 4. If matched but key changed -> return defer.fail(error.HostKeyChanged(...))
            # 5. If not found:
            #    a) Strict checking: return defer.fail(error.HostKeyNotVerifiable(...))
            #    b) Trust on first use (prompt user): Ask user, if yes, add to known_hosts
            #       and return defer.succeed(True). If no, return defer.fail(...)
            # -----------------------------------------------------
            log.msg("ERROR: Strict host key checking enabled, but no verification logic implemented.")
            log.msg("Please add verification against known_hosts or use --insecure for testing.")
            # Fail verification if not explicitly insecure
            return defer.fail(
                failure.Failure(keys.BadHostKey("Host key verification failed (strict mode)"))
            )

    def connectionSecure(self):
        """Called when the cryptographic transport layer is secure."""
        log.msg("SSH Transport secured. Requesting user authentication service.")
        # Initiate the authentication process
        password_auth = ClientPasswordAuth(
            self._config.username,
            self._config.password,
            self._connection_service # Pass the instantiated connection service
        )
        self.requestService(password_auth)

    def connectionLost(self, reason: failure.Failure):
        """Called when the underlying TCP connection is lost."""
        log.msg(f"SSH Transport connection lost: {reason.getErrorMessage()}")
        # Ensure the main deferred is errbacked if the connection drops unexpectedly
        # The connection_service or channel should ideally handle this via their stop/closed methods,
        # but this is a fallback.
        if hasattr(self._connection_service, '_completion_deferred') and \
           not self._connection_service._completion_deferred.called:
            self._connection_service._completion_deferred.errback(reason)
        # Call superclass method
        transport.SSHClientTransport.connectionLost(self, reason)


class SSHCommandClientFactory(protocol.ClientFactory):
    """Factory responsible for creating the SSH transport protocol instance."""
    def __init__(self, config: SSHClientConfig):
        self.config = config
        # Deferred to signal completion or failure of the entire operation
        self.completion_deferred = defer.Deferred()
        log.msg("ClientFactory initialized.")

    def buildProtocol(self, addr) -> Optional[protocol.Protocol]:
        """Creates the protocol instance when TCP connection is established."""
        log.msg(f"Connected to {addr}. Building SSH protocol.")
        try:
            # Instantiate the connection service here, pass it the deferred
            connection_service = ClientCommandConnection(
                self.config.command, self.completion_deferred
            )
            # Instantiate the transport, pass config and the connection service
            proto = SecureClientTransport(self.config, connection_service)
            return proto
        except Exception as e:
             log.err(e, "Failed to build protocol")
             # If buildProtocol fails, signal failure immediately
             self.completion_deferred.errback(failure.Failure(e))
             return None # Returning None stops the connection attempt


    def clientConnectionFailed(self, connector, reason: failure.Failure):
        """Called if the TCP connection itself fails."""
        log.err(reason, f"Failed to connect to {self.config.server}:{self.config.port}")
        # Signal failure via the main deferred
        if not self.completion_deferred.called:
            self.completion_deferred.errback(reason)

    def clientConnectionLost(self, connector, reason: failure.Failure):
        """Called if the TCP connection is lost *after* it was established."""
        # This is often handled by protocol.connectionLost, but can be logged here too.
        log.msg(f"Client connection lost: {reason.getTraceback()}")
        # Ensure completion deferred is called if not already
        if not self.completion_deferred.called:
             # Could be a normal disconnect after command finishes, or an error.
             # The channel/service stopping should normally handle this.
             # If it reaches here without being called, assume unexpected disconnect.
             log.msg("Connection lost unexpectedly before command completion signaled.")
             err = failure.Failure(Exception(f"Connection lost unexpectedly: {reason.getErrorMessage()}"))
             self.completion_deferred.errback(err)

# --- Application Entry Point ---

def main():
    """Parses arguments, sets up logging, starts the client, and runs the reactor."""
    parser = argparse.ArgumentParser(
        description="Execute a command on a remote server via SSH using password auth."
    )
    parser.add_argument("server", help="SSH server hostname or IP address")
    parser.add_argument("command", help="Command to execute on the remote server")
    parser.add_argument("-p", "--port", type=int, default=22, help="SSH server port (default: 22)")
    parser.add_argument("-u", "--username", help="SSH username (will prompt if not provided)")
    parser.add_argument("--password", help="SSH password (will prompt securely if not provided)")
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable host key verification (INSECURE, for testing only!)"
    )
    parser.add_argument(
        "--log",
        default="-", # Default to stdout
        help="Log file path ('-' for stdout)"
    )
    args = parser.parse_args()

    # Setup logging
    log_target = sys.stdout if args.log == "-" else open(args.log, 'a')
    log.startLogging(log_target)

    # Get credentials securely if not provided
    username = args.username or input("Username: ")
    # Use getpass for secure password input if not supplied via argument
    password = args.password or getpass.getpass(f"Password for {username}@{args.server}: ")

    # Create configuration object (Dependency Injection)
    config = SSHClientConfig(
        server=args.server,
        port=args.port,
        username=username,
        password=password,
        command=args.command,
        insecure=args.insecure
    )

    # Create the factory
    factory = SSHCommandClientFactory(config)

    # --- Set up Deferred callbacks for completion/failure ---
    def on_success(result):
        log.msg("Command execution successful.")
        # Result contains the buffered output if needed
        # print("\n--- Command Output (Buffered) ---")
        # print(result)
        # print("--- End Output ---")
        reactor.stop()

    def on_failure(reason: failure.Failure):
        log.err(reason, "Command execution failed")
        print(f"\nError: {reason.getErrorMessage()}", file=sys.stderr)
        # Optionally print full traceback for debugging
        # print(reason.getTraceback(), file=sys.stderr)
        reactor.stop()
        sys.exit(1) # Exit with error code

    factory.completion_deferred.addCallbacks(on_success, on_failure)

    # Initiate connection
    log.msg(f"Connecting to {config.server}:{config.port}...")
    reactor.connectTCP(config.server, config.port, factory)

    # Start the Twisted event loop
    reactor.run()

if __name__ == "__main__":
    try:
        main()
    except net_error.CannotListenError as e:
         print(f"Error: {e}", file=sys.stderr)
         sys.exit(2)
    except KeyboardInterrupt:
         print("\nInterrupted by user.", file=sys.stderr)
         # Attempt to stop the reactor gracefully if it's running
         if reactor.running:
              reactor.callFromThread(reactor.stop) # Stop reactor safely
         sys.exit(1)
    except Exception as e:
        # Catch-all for unexpected errors during setup
        print(f"An unexpected critical error occurred: {e}", file=sys.stderr)
        log.err(e, "Unhandled exception in main execution block")
        sys.exit(3)
