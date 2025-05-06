"""
Read-only mount checker.

This module provides a tool for monitoring filesystems on remote systems
to detect any filesystems that are mounted as read-only, which can indicate
filesystem corruption or other serious issues.

Typical usage:
    $ python -m opsforge.filesystem.readonly --host example.com --user admin

For more options:
    $ python -m opsforge.filesystem.readonly --help
"""

import sys
import os
import argparse
import re
import socket
from typing import List, Optional, Sequence, Tuple, Set, Dict
from dataclasses import dataclass, field
import paramiko

from opsforge.common.logging import setup_logging, get_logger
from opsforge.common.exceptions import OpsForgeError, NetworkError

# Set up logger
logger = get_logger(__name__)

# Constants
EXIT_OK = 0
EXIT_WARNING = 1
EXIT_CRITICAL = 2
EXIT_ERROR = 3

# Domain/Value Objects
@dataclass(frozen=True)
class SSHConfig:
    """Configuration for SSH connection."""
    host: str
    user: str
    port: int
    identity_file: Optional[str] = None
    password: Optional[str] = None
    timeout: int = 10


@dataclass(frozen=True)
class MountInfo:
    """Represents a single mount point entry."""
    device: str
    mountpoint: str
    filesystem_type: str
    options: List[str]
    # Ignoring dump and passno fields

    @classmethod
    def from_line(cls, line: str) -> Optional['MountInfo']:
        """
        Parses a line from /proc/mounts or similar.
        
        Args:
            line: A line from a mount table file.
            
        Returns:
            MountInfo object or None if the line cannot be parsed.
        """
        parts = re.split(r'\s+', line.strip())
        if len(parts) >= 4:
            return cls(
                device=parts[0],
                mountpoint=parts[1],
                filesystem_type=parts[2],
                options=parts[3].split(',')
            )
        return None

    def is_read_only(self) -> bool:
        """
        Checks if the mount options include 'ro'.
        
        Returns:
            True if the mount is read-only, False otherwise.
        """
        return 'ro' in self.options


@dataclass(frozen=True)
class CheckConfig:
    """Configuration for the mount check operation."""
    ssh_config: SSHConfig
    mount_tab_path: str
    partition_filters: Optional[List[str]] = None
    exclude_filter: Optional[str] = None
    exclude_types: Set[str] = field(default_factory=set)


# Custom Exceptions
class SSHExecutionError(NetworkError):
    """Error during SSH command execution."""
    def __init__(self, message: str, stderr: str = ""):
        super().__init__(message)
        self.stderr = stderr


# Infrastructure/Services
class SSHCommandExecutor:
    """Executes commands remotely via SSH using Paramiko."""
    
    def __init__(self, config: SSHConfig):
        """
        Initialize with SSH configuration.
        
        Args:
            config: SSH connection configuration.
        """
        self._config = config
        self._client = None

    def _connect(self) -> paramiko.SSHClient:
        """
        Establish an SSH connection.
        
        Returns:
            Connected SSHClient.
            
        Raises:
            SSHExecutionError: If the connection fails.
        """
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            connect_kwargs = {
                'hostname': self._config.host,
                'username': self._config.user,
                'port': self._config.port,
                'timeout': self._config.timeout,
            }
            
            # Add password if provided
            if self._config.password:
                connect_kwargs['password'] = self._config.password
                
            # Add identity file if provided
            if self._config.identity_file:
                connect_kwargs['key_filename'] = self._config.identity_file
                
            client.connect(**connect_kwargs)
            return client
            
        except paramiko.AuthenticationException:
            raise SSHExecutionError(f"Authentication failed for {self._config.user}@{self._config.host}")
        except paramiko.SSHException as e:
            raise SSHExecutionError(f"SSH error: {str(e)}")
        except socket.error as e:
            raise SSHExecutionError(f"Socket error when connecting to {self._config.host}: {str(e)}")
        except Exception as e:
            raise SSHExecutionError(f"Unexpected error establishing SSH connection: {str(e)}")

    def execute(self, command: str) -> str:
        """
        Executes a command on the configured remote host using Paramiko.

        Args:
            command: The command to execute on the remote host.

        Returns:
            The stdout of the executed command.
            
        Raises:
            SSHExecutionError: If the SSH command fails.
        """
        logger.debug(f"Executing SSH command: {command}")
        
        try:
            client = self._connect()
            
            # Execute the command
            stdin, stdout, stderr = client.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            
            # Read output
            stdout_data = stdout.read().decode('utf-8')
            stderr_data = stderr.read().decode('utf-8')
            
            # Close the connection
            client.close()
            
            if exit_status != 0:
                error_message = (
                    f"Command failed with exit code {exit_status} "
                    f"on host {self._config.host}"
                )
                logger.error(f"{error_message}")
                if stderr_data:
                    logger.error(f"stderr: {stderr_data.strip()}")
                raise SSHExecutionError(error_message, stderr_data)
                
            return stdout_data
            
        except SSHExecutionError:
            # Re-raise existing SSH execution errors
            raise
        except Exception as e:
            error_message = f"An unexpected error occurred during SSH execution: {str(e)}"
            logger.exception(error_message)
            raise SSHExecutionError(error_message)


class MountService:
    """Handles fetching, parsing, and filtering mount information."""

    def __init__(self, executor: SSHCommandExecutor):
        """
        Initialize with SSH executor.
        
        Args:
            executor: SSH command executor for remote operations.
        """
        self._executor = executor

    def get_remote_mounts(self, mount_tab_path: str) -> List[MountInfo]:
        """
        Fetches and parses mount information from the remote system.
        
        Args:
            mount_tab_path: Path to the mount table file on the remote system.
            
        Returns:
            List of MountInfo objects representing mounts on the remote system.
            
        Raises:
            SSHExecutionError: If fetching mount information fails.
        """
        command = f"cat {mount_tab_path}"
        try:
            raw_output = self._executor.execute(command)
        except SSHExecutionError as e:
            logger.error(f"Failed to retrieve mount info: {e}")
            if e.stderr:
                logger.error(f"SSH stderr: {e.stderr.strip()}")
            raise

        mounts = []
        for line in raw_output.strip().splitlines():
            if not line or line.startswith('#'):  # Skip empty lines/comments
                continue
            mount_info = MountInfo.from_line(line)
            if mount_info:
                mounts.append(mount_info)
            else:
                logger.warning(f"Could not parse mount line: {line}")
        
        logger.info(f"Retrieved {len(mounts)} mounts from remote system")
        return mounts

    def filter_mounts(self, mounts: List[MountInfo], config: CheckConfig) -> List[MountInfo]:
        """
        Filters the list of mounts based on the provided configuration.
        
        Args:
            mounts: List of mounts to filter.
            config: Configuration specifying filtering criteria.
            
        Returns:
            Filtered list of MountInfo objects.
        """
        filtered = []
        for mount in mounts:
            # Filesystem type exclusion
            if mount.filesystem_type in config.exclude_types:
                logger.debug(f"Skipping {mount.mountpoint} (type: {mount.filesystem_type}) due to excluded filesystem type")
                continue

            # Partition/Device filtering logic
            if config.partition_filters:
                # If partition filters are specified, only include matching devices/paths
                if not any(patt in mount.device or patt in mount.mountpoint for patt in config.partition_filters):
                    logger.debug(f"Skipping {mount.mountpoint} as it doesn't match any partition filter")
                    continue
                # If it matched a partition filter, include it
            elif config.exclude_filter:
                # If no partition filters but exclude filter is specified
                if config.exclude_filter in mount.device or config.exclude_filter in mount.mountpoint:
                    logger.debug(f"Skipping {mount.mountpoint} due to exclude filter match")
                    continue

            # If we passed all filters, add the mount
            filtered.append(mount)

        logger.info(f"After filtering: {len(filtered)} mounts remaining")
        return filtered

    def find_read_only_mounts(self, mounts: List[MountInfo]) -> List[MountInfo]:
        """
        Identifies read-only mounts from a list.
        
        Args:
            mounts: List of mounts to check.
            
        Returns:
            List of read-only MountInfo objects.
        """
        ro_mounts = [mount for mount in mounts if mount.is_read_only()]
        logger.info(f"Found {len(ro_mounts)} read-only mounts")
        return ro_mounts


def parse_arguments() -> CheckConfig:
    """
    Parses command-line arguments into a configuration object.
    
    Returns:
        CheckConfig object with parsed arguments.
    """
    parser = argparse.ArgumentParser(description='Check read-only mounts on a remote system.')
    
    # SSH connection options
    ssh_group = parser.add_argument_group('SSH Options')
    ssh_group.add_argument('--host', '-H', required=True, help='SSH Remote host')
    ssh_group.add_argument('--user', '-u', default='root', help='SSH Remote user (default: root)')
    ssh_group.add_argument('--port', '-p', type=int, default=22, help='SSH Remote port (default: 22)')
    ssh_group.add_argument('--identity', '-i', help='SSH identity file')
    ssh_group.add_argument('--password', help='SSH password (not recommended, use identity file instead)')
    ssh_group.add_argument('--timeout', type=int, default=10, help='SSH connection timeout in seconds (default: 10)')
    
    # Mount check options
    mount_group = parser.add_argument_group('Mount Check Options')
    mount_group.add_argument('--mount-table', '-m', default='/proc/mounts', 
                            help='Mount table path (default: /proc/mounts)')
    mount_group.add_argument('--partition', '-P', action='append', dest='part_filter',
                            help='Pattern of partition to check (may be repeated)')
    mount_group.add_argument('--exclude', '-x', dest='exclude',
                            help='Pattern of partition to ignore (only when --partition not used)')
    mount_group.add_argument('--exclude-type', '-X', action='append', dest='exclude_type',
                            help='File system types to exclude (may be repeated)')
    
    # Backward compatibility (old parameter names)
    parser.add_argument('-sh', dest='sHost', help=argparse.SUPPRESS)
    parser.add_argument('-su', dest='sUser', help=argparse.SUPPRESS)
    parser.add_argument('-sp', type=int, dest='sPort', help=argparse.SUPPRESS)
    parser.add_argument('-mpath', dest='mtabPath', help=argparse.SUPPRESS)
    parser.add_argument('-partition', action='append', dest='partFilter', help=argparse.SUPPRESS)

    args = parser.parse_args()

    # Handle backward compatibility
    host = args.host if args.host else args.sHost
    user = args.user if args.user else args.sUser
    port = args.port if args.port else args.sPort
    mount_table = args.mount_table if args.mount_table else args.mtabPath
    part_filters = args.part_filter if args.part_filter else args.partFilter

    if not host:
        parser.error("SSH host is required (--host)")

    ssh_config = SSHConfig(
        host=host,
        user=user if user else 'root',
        port=port if port else 22,
        identity_file=args.identity,
        password=args.password,
        timeout=args.timeout
    )
    
    # Convert exclude_type list to set for faster lookups
    exclude_types = set()
    if args.exclude_type:
        exclude_types.update(args.exclude_type)
    
    return CheckConfig(
        ssh_config=ssh_config,
        mount_tab_path=mount_table if mount_table else '/proc/mounts',
        partition_filters=part_filters,
        exclude_filter=args.exclude,
        exclude_types=exclude_types
    )


def main() -> int:
    """
    Main script execution logic.
    
    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    # Set up logging
    setup_logging(log_level=os.getenv("OPSFORGE_LOG_LEVEL", "INFO"))
    
    try:
        # Parse arguments and set up services
        config = parse_arguments()
        logger.info(f"Checking for read-only mounts on {config.ssh_config.host}")
        
        ssh_executor = SSHCommandExecutor(config.ssh_config)
        mount_service = MountService(ssh_executor)

        # Get and filter mounts
        all_mounts = mount_service.get_remote_mounts(config.mount_tab_path)
        filtered_mounts = mount_service.filter_mounts(all_mounts, config)
        ro_mounts = mount_service.find_read_only_mounts(filtered_mounts)

        # Output results and set exit code
        if ro_mounts:
            ro_devices = ', '.join(f"{mount.device} on {mount.mountpoint}" for mount in ro_mounts)
            print(f"RO_MOUNTS CRITICAL - Found ro mounts: {ro_devices}")
            return EXIT_CRITICAL
        else:
            print("RO_MOUNTS OK - No ro mounts found")
            return EXIT_OK

    except SSHExecutionError as e:
        print(f"RO_MOUNTS ERROR - SSH error: {e}", file=sys.stderr)
        return EXIT_ERROR
    except Exception as e:
        logger.exception(f"An unexpected error occurred")
        print(f"RO_MOUNTS ERROR - {e}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())