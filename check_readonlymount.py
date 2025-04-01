#!/usr/bin/env python3

import sys
import argparse
import subprocess
import re
from typing import List, Optional, Sequence, Tuple
from dataclasses import dataclass, field

# --- Constants ---
EXIT_OK = 0
EXIT_CRITICAL = 2
EXIT_ERROR = 3 # Generic/SSH errors

# --- Domain/Value Objects ---

@dataclass(frozen=True)
class SSHConfig:
    """Configuration for SSH connection."""
    host: str
    user: str
    port: int

@dataclass(frozen=True)
class MountInfo:
    """Represents a single mount point entry."""
    device: str
    mountpoint: str
    filesystem_type: str
    options: List[str]
    # Ignoring dump and passno fields for now (parts[4], parts[5])

    @classmethod
    def from_line(cls, line: str) -> Optional['MountInfo']:
        """Parses a line from /proc/mounts or similar."""
        parts = re.split(r'\s+', line.strip())
        if len(parts) >= 4:
            return cls(
                device=parts[0],
                mountpoint=parts[1],
                filesystem_type=parts[2],
                options=parts[3].split(',')
            )
        return None # Return None for lines that cannot be parsed

    def is_read_only(self) -> bool:
        """Checks if the mount options include 'ro'."""
        return 'ro' in self.options

@dataclass(frozen=True)
class CheckConfig:
    """Configuration for the mount check operation."""
    ssh_config: SSHConfig
    mount_tab_path: str
    partition_filters: Optional[List[str]] = None
    exclude_filter: Optional[str] = None
    exclude_types: Optional[List[str]] = field(default_factory=list)
    # skip_date_check: bool = False # Kept parsing, but not used in core logic

# --- Infrastructure/Services ---

class SSHExecutionError(Exception):
    """Custom exception for SSH command failures."""
    def __init__(self, message: str, stderr: str = ""):
        super().__init__(message)
        self.stderr = stderr

class SSHCommandExecutor:
    """Executes commands remotely via SSH."""
    def __init__(self, config: SSHConfig):
        self._config = config

    def execute(self, command: str) -> str:
        """
        Executes a command on the configured remote host.

        Raises:
            SSHExecutionError: If the SSH command fails.
        Returns:
            The stdout of the executed command.
        """
        ssh_command = [
            'ssh',
            f'{self._config.user}@{self._config.host}',
            '-p', str(self._config.port),
            command
        ]
        try:
            result = subprocess.run(
                ssh_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True, # Raises CalledProcessError on non-zero exit
                text=True,
                encoding='utf-8' # Be explicit about encoding
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            error_message = (
                f"SSH command failed with exit code {e.returncode} "
                f"on host {self._config.host}"
            )
            raise SSHExecutionError(error_message, e.stderr) from e
        except FileNotFoundError:
            # Handle case where 'ssh' command is not found
            raise SSHExecutionError(f"'ssh' command not found. Is it installed and in PATH?")
        except Exception as e:
            # Catch other potential errors during subprocess execution
            raise SSHExecutionError(f"An unexpected error occurred during SSH execution: {e}") from e


class MountService:
    """Handles fetching, parsing, and filtering mount information."""

    def __init__(self, executor: SSHCommandExecutor):
        self._executor = executor

    def get_remote_mounts(self, mount_tab_path: str) -> List[MountInfo]:
        """Fetches and parses mount information from the remote system."""
        command = f"cat {mount_tab_path}"
        try:
            raw_output = self._executor.execute(command)
        except SSHExecutionError as e:
            # Re-raise with more context or handle differently if needed
            print(f"ERROR: Failed to retrieve mount info: {e}", file=sys.stderr)
            if e.stderr:
                print(f"SSH stderr: {e.stderr.strip()}", file=sys.stderr)
            sys.exit(EXIT_ERROR) # Exit here if fetching fails fundamentally

        mounts = []
        for line in raw_output.strip().splitlines():
            if not line or line.startswith('#'): # Skip empty lines/comments
                continue
            mount_info = MountInfo.from_line(line)
            if mount_info:
                mounts.append(mount_info)
            else:
                # Log or warn about lines that couldn't be parsed
                print(f"WARNING: Could not parse mount line: {line}", file=sys.stderr)
        return mounts

    def filter_mounts(self, mounts: List[MountInfo], config: CheckConfig) -> List[MountInfo]:
        """Filters the list of mounts based on the provided configuration."""
        filtered = []
        for mount in mounts:
            # Filesystem type exclusion
            if config.exclude_types and mount.filesystem_type in config.exclude_types:
                continue

            # Partition/Device filtering logic
            # Note: Original help text implies -x only works if -partition is unspecified.
            # This implementation follows the *code* logic which applies -x regardless,
            # unless a -partition filter *explicitly matches* the device first.
            if config.partition_filters:
                # If -partition is specified, only include matching devices/paths
                if not any(patt in mount.device or patt in mount.mountpoint for patt in config.partition_filters):
                     # ^ Assuming filter can apply to device OR mountpoint based on 'path or partition' help text
                    continue
                # If it matched a partition filter, it's included (exclude_filter doesn't apply here per help text)

            elif config.exclude_filter:
                # If -partition is *not* specified, apply the -x exclude filter
                 if config.exclude_filter in mount.device or config.exclude_filter in mount.mountpoint:
                      # ^ Assuming filter can apply to device OR mountpoint
                    continue

            # If we passed all filters, add the mount
            filtered.append(mount)

        return filtered

    def find_read_only_mounts(self, mounts: List[MountInfo]) -> List[MountInfo]:
        """Identifies read-only mounts from a list."""
        return [mount for mount in mounts if mount.is_read_only()]


# --- Application Layer / Main Execution ---

def parse_arguments() -> CheckConfig:
    """Parses command-line arguments into a configuration object."""
    parser = argparse.ArgumentParser(description='Check read-only mounts on a remote system.')
    parser.add_argument('-sh', required=True, dest='sHost', help='SSH Remote host')
    parser.add_argument('-su', dest='sUser', default='zenoss', help='SSH Remote user (default: zenoss)')
    parser.add_argument('-sp', dest='sPort', type=int, default=22, help='SSH Remote port (default: 22)')
    # parser.add_argument('-sd', action='store_true', dest='skipdate', help='Disable additional check (echo/cat)', required=False) # Parsed but not used
    parser.add_argument('-mpath', dest='mtabPath', default='/proc/mounts', help='Use this mtab instead (default is /proc/mounts)')
    parser.add_argument('-partition', action='append', dest='partFilter', help='Glob pattern of path or partition to check (may be repeated)')
    parser.add_argument('-x', dest='exclude', help='Glob pattern of path or partition to ignore (only works if -partition unspecified)')
    parser.add_argument('-X', action='append', dest='exclude_type', help='File system types to exclude')

    args = parser.parse_args()

    ssh_config = SSHConfig(host=args.sHost, user=args.sUser, port=args.sPort)
    return CheckConfig(
        ssh_config=ssh_config,
        mount_tab_path=args.mtabPath,
        partition_filters=args.partFilter,
        exclude_filter=args.exclude,
        exclude_types=args.exclude_type or [], # Ensure it's a list
        # skip_date_check=args.skipdate # Store if needed later
    )

def main() -> None:
    """Main script execution logic."""
    try:
        config = parse_arguments()
        ssh_executor = SSHCommandExecutor(config.ssh_config)
        mount_service = MountService(ssh_executor)

        all_mounts = mount_service.get_remote_mounts(config.mount_tab_path)
        filtered_mounts = mount_service.filter_mounts(all_mounts, config)
        ro_mounts = mount_service.find_read_only_mounts(filtered_mounts)

        if ro_mounts:
            ro_devices = ', '.join(mount.device for mount in ro_mounts)
            print(f"RO_MOUNTS CRITICAL - Found ro mounts: {ro_devices}")
            sys.exit(EXIT_CRITICAL)
        else:
            print("RO_MOUNTS OK - No ro mounts found")
            sys.exit(EXIT_OK)

    except SSHExecutionError as e:
        # Already printed details in get_remote_mounts or directly from executor if raised there
        # If needed, print more here: print(f"Error during SSH operation: {e}", file=sys.stderr)
        sys.exit(EXIT_ERROR) # Exit with generic error code
    except Exception as e:
        # Catch-all for unexpected errors during processing (e.g., parsing, filtering)
        print(f"An unexpected application error occurred: {e}", file=sys.stderr)
        # Potentially add traceback here for debugging if needed
        # import traceback
        # traceback.print_exc()
        sys.exit(EXIT_ERROR)


if __name__ == "__main__":
    main()
