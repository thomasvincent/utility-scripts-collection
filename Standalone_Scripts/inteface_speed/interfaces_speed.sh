#!/bin/bash
#
# Description:
#   This script identifies non-loopback network interfaces, retrieves their link
#   speed using 'ethtool', converts the speed to a standardized unit (kbit/s),
#   and reports the results.
#
# Dependencies:
#   - bash (v4.0+ recommended for potential associative arrays, though not used here)
#   - ethtool: Utility for querying network device settings.
#   - iproute2 (provides 'ip'): Modern utility for IP configuration (preferred over 'ifconfig').
#   - coreutils (grep, awk, sed): Standard text processing utilities.
#
# Usage:
#   ./script_name.sh
#
# Exit Codes:
#   0: Success
#   1: Missing dependency ('ethtool')
#   2: Error retrieving network interfaces
#   3: Error during interface processing (details logged to stderr)
#
set -euo pipefail # Exit on error, treat unset variables as error, pipe fails if any command fails

# --- Configuration ---
readonly TARGET_UNIT="kbit/s" # Standard unit for output speed

# --- Domain: Network Interface Representation ---
# We are primarily interested in the Interface Name (string) and its Speed (integer, in kbit/s).

# --- Infrastructure: System Interaction ---

# Function: error_exit
# Description: Prints an error message to stderr and exits the script.
# Arguments:
#   $1: The error message string.
#   $2: (Optional) The exit code (default: 1).
error_exit() {
    local message="${1}"
    local exit_code="${2:-1}"
    echo "ERROR: ${message}" >&2
    exit "${exit_code}"
}

# Function: ensure_command_exists
# Description: Checks if a command is available in the system's PATH. Exits if not found.
# Arguments:
#   $1: The command name to check.
ensure_command_exists() {
    local cmd="${1}"
    if ! command -v "${cmd}" >/dev/null 2>&1; then
        error_exit "'${cmd}' command not found. Please install it." 1
    fi
}

# Function: get_network_interfaces
# Description: Retrieves a list of non-loopback network interface names.
#              Uses the 'ip' command for better compatibility with modern systems.
#              Outputs each interface name on a new line.
# Returns:
#   Prints interface names to stdout. Exits with code 2 on failure.
get_network_interfaces() {
    local interfaces
    # Using 'ip link show' is generally preferred over 'ifconfig'
    # 1. Get link info.
    # 2. Filter lines starting with a digit (interface index).
    # 3. Exclude the loopback interface ('lo:').
    # 4. Extract the second field (interface name with ':').
    # 5. Remove the trailing colon.
    # 6. Remove '@<parent>' part for VLANs/virtual interfaces if present.
    interfaces=$(ip -o link show | awk -F': ' '!/ lo:/{print $2}' | sed 's/@.*//' )

    if [[ -z "${interfaces}" ]]; then
        error_exit "Could not retrieve any non-loopback network interfaces." 2
    fi
    echo "${interfaces}"
}

# Function: get_interface_speed_raw
# Description: Uses 'ethtool' to get the raw speed string for a given interface.
# Arguments:
#   $1: The name of the network interface.
# Returns:
#   Prints the raw speed string (e.g., "1000Mb/s") to stdout if found.
#   Returns an empty string if speed is not available or 'ethtool' fails for that interface.
#   Prints warnings to stderr if 'ethtool' fails or speed is not found.
get_interface_speed_raw() {
    local interface_name="${1}"
    local speed_line
    local raw_speed=""

    # Run ethtool, capture output and exit status
    # Redirect stderr to /dev/null unless debugging is needed
    if ! speed_line=$(ethtool "${interface_name}" 2>/dev/null | grep -o 'Speed:.*'); then
        echo "Warning: 'ethtool' failed or provided no output for ${interface_name}." >&2
        echo "" # Return empty string on failure
        return 0 # Indicate handled condition, not script failure
    fi

    # Extract the speed value part
    if [[ "${speed_line}" =~ Speed:\ *([0-9]+(Mb/s|Gb/s|Kb/s)|Unknown!?) ]]; then
         raw_speed="${BASH_REMATCH[1]}"
         # Handle 'Unknown!' explicitly if needed, though it won't parse later
         if [[ "${raw_speed}" == "Unknown!" ]]; then
             echo "Warning: Speed reported as 'Unknown!' for ${interface_name}." >&2
             raw_speed="" # Treat as empty/unparseable
         fi
    else
        echo "Warning: Could not parse speed information from 'ethtool' output for ${interface_name}." >&2
        # Example ethtool output line: "Speed: 1000Mb/s"
    fi

    echo "${raw_speed}"
}


# --- Domain Logic: Speed Processing ---

# Function: parse_and_convert_speed
# Description: Parses a raw speed string (value + unit) and converts it to kbit/s.
# Arguments:
#   $1: The raw speed string (e.g., "1000Mb/s", "10Gb/s").
# Returns:
#   Prints the speed converted to kbit/s (integer) to stdout.
#   Returns an empty string if parsing or conversion fails (e.g., unknown unit).
parse_and_convert_speed() {
    local raw_speed="${1}"
    local numeric_speed=""
    local unit=""
    local speed_kbps=""

    # Extract numeric value and unit using parameter expansion or regex
    if [[ "${raw_speed}" =~ ^([0-9]+)(Mb/s|Gb/s|Kb/s)$ ]]; then
        numeric_speed="${BASH_REMATCH[1]}"
        unit="${BASH_REMATCH[2]}"
    else
        # If no match (empty input, "Unknown!", or unexpected format)
        echo "" # Return empty string indicating failure to parse
        return 0 # Handled condition
    fi

    # Convert to kbit/s based on the unit
    case "${unit}" in
        "Mb/s")
            # Bash arithmetic doesn't handle floats, ensure integer multiplication
            speed_kbps=$(( numeric_speed * 1000 ))
            ;;
        "Gb/s")
            speed_kbps=$(( numeric_speed * 1000 * 1000 ))
            ;;
        "Kb/s")
             # Already in kbit/s, but named Kb/s - treat as kbit/s
            speed_kbps="${numeric_speed}"
           ;;
        *)
            # Should not happen if regex matched, but good practice
            echo "Warning: Encountered unknown speed unit '${unit}' for value '${numeric_speed}'." >&2
            speed_kbps="" # Return empty string for unknown units
            ;;
    esac

    echo "${speed_kbps}"
}


# --- Application Logic: Main Execution ---

main() {
    # 1. Check Dependencies
    ensure_command_exists "ethtool"
    ensure_command_exists "ip"
    ensure_command_exists "awk"
    ensure_command_exists "grep"
    ensure_command_exists "sed" # Used in get_network_interfaces

    # 2. Get Interfaces
    local interfaces
    # Readarray/mapfile is safer for reading lines into an array
    mapfile -t interfaces < <(get_network_interfaces)

    if [[ ${#interfaces[@]} -eq 0 ]]; then
       echo "No network interfaces found to process."
       exit 0 # Not an error, just nothing to do
    fi

    echo "Processing network interface speeds..."
    local overall_status=0 # Track if any interface processing failed

    # 3. Process Each Interface
    local interface_name
    for interface_name in "${interfaces[@]}"; do
        echo "--- Processing Interface: ${interface_name} ---"

        # 3a. Get Raw Speed (Infrastructure)
        local raw_speed
        raw_speed=$(get_interface_speed_raw "${interface_name}")

        if [[ -z "${raw_speed}" ]]; then
            echo "Skipping ${interface_name}: Could not determine raw speed." >&2
            overall_status=3 # Mark as partial failure
            continue # Move to the next interface
        fi

        # 3b. Parse and Convert Speed (Domain Logic)
        local speed_kbps
        speed_kbps=$(parse_and_convert_speed "${raw_speed}")

        # 3c. Report Result
        if [[ -n "${speed_kbps}" ]]; then
            echo "Interface ${interface_name}: Speed = ${speed_kbps} ${TARGET_UNIT} (from ${raw_speed})"
        else
            echo "Skipping ${interface_name}: Failed to parse/convert speed '${raw_speed}'." >&2
            overall_status=3 # Mark as partial failure
        fi
    done

    echo "--- Processing Complete ---"
    exit "${overall_status}" # Exit 0 if all ok, 3 if any interface had issues
}

# --- Script Entry Point ---
main "$@"
