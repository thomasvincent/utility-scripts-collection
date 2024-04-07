#!/usr/bin/env python3

import sys
import argparse
import subprocess
import datetime
import re

def parse_arguments():
    parser = argparse.ArgumentParser(description='Check read-only mounts on a remote system.')
    parser.add_argument('-sh', required=True, dest='sHost', help='SSH Remote host')
    parser.add_argument('-su', dest='sUser', default='zenoss', help='SSH Remote user (default: zenoss)')
    parser.add_argument('-sp', dest='sPort', type=int, default=22, help='SSH Remote port (default: 22)')
    parser.add_argument('-sd', action='store_true', dest='skipdate', help='Disable additional check (echo/cat)', required=False)
    parser.add_argument('-mpath', dest='mtabPath', default='/proc/mounts', help='Use this mtab instead (default is /proc/mounts)')
    parser.add_argument('-partition', action='append', dest='partFilter', help='Glob pattern of path or partition to check (may be repeated)')
    parser.add_argument('-x', dest='exclude', help='Glob pattern of path or partition to ignore (only works if -partition unspecified)')
    parser.add_argument('-X', action='append', dest='exclude_type', help='File system types to exclude')
    return parser.parse_args()

def execute_ssh_command(command, host, user, port):
    ssh_command = ['ssh', f'{user}@{host}', '-p', str(port), command]
    try:
        result = subprocess.run(ssh_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing SSH command: {e}")
        sys.exit(3)

def filter_mounts(mounts, partition_filters, exclude, exclude_types):
    filtered_mounts = []

    for mount in mounts:
        if partition_filters and not any(part in mount['device'] for part in partition_filters):
            continue
        if exclude and exclude in mount['device']:
            continue
        if exclude_types and mount['type'] in exclude_types:
            continue
        filtered_mounts.append(mount)

    return filtered_mounts

def transform_to_dicts(mounts_raw):
    mounts_list = []
    for line in mounts_raw.strip().split('\n'):
        parts = re.split('\s+', line)
        if len(parts) >= 6:
            mounts_list.append({
                'device': parts[0], 'mountpoint': parts[1], 'type': parts[2], 'opts': parts[3], 'n1': parts[4], 'n2': parts[5]
            })
    return mounts_list

def check_ro_mounts(mounts):
    ro_mounts = [mount for mount in mounts if 'ro' in mount['opts'].split(',')]
    return ', '.join(mount['device'] for mount in ro_mounts)

def main():
    args = parse_arguments()

    ssh_output = execute_ssh_command(f"cat {args.mtabPath}", args.sHost, args.sUser, args.sPort)
    mounts = transform_to_dicts(ssh_output)
    mounts = filter_mounts(mounts, args.partFilter, args.exclude, args.exclude_type)
    ro_mounts_str = check_ro_mounts(mounts)

    if ro_mounts_str:
        print(f"RO_MOUNTS CRITICAL - Found ro mounts: {ro_mounts_str}")
        sys.exit(2)
    else:
        print("RO_MOUNTS OK - No ro mounts found")
        sys.exit(0)

if __name__ == "__main__":
    main()
