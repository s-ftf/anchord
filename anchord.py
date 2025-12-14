#!/usr/bin/env python3
import subprocess
import time
import json
import os
import re
import requests
import shutil
import errno
from pygments import highlight
from pygments.lexers import JsonLexer
from pygments.formatters import Terminal256Formatter
from packaging.version import parse as parse_version
from pygments.token import Token
from pygments.style import Style
from pygments.formatter import Formatter
from io import StringIO



def load_daemon_config(path="daemons.json"):
    with open(path, "r") as f:
        return json.load(f)

daemons = load_daemon_config()

class ErrStyle(Style):
    default_style = ""
    styles = {
        Token.Generic.Error: "bold ansired",
    }

_fmt = Terminal256Formatter(style=ErrStyle)

def red_error(text: str) -> str:
    buf = StringIO()
    _fmt.format([(Token.Generic.Error, text)], buf)
    return buf.getvalue()

def _expand_abs(path: str) -> str:
    if not path:
        return path
    path = os.path.expanduser(path)
    if os.path.isabs(path):
        return path
    # Resolve relative to the script directory, not the current working dir
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(base, path))

def _is_gvfs_path(path: str) -> bool:
    # Common indicator for GVFS SFTP mounts on Linux
    return path.startswith("/run/user/") and "/gvfs/" in path

def resolve_executable(path: str) -> str | None:
    """
    Accept absolute/relative paths or bare program names.
    Returns an absolute path if resolvable and executable, else None.
    """
    if not path:
        return None
    p = _expand_abs(path)

    # If it looks like a bare name (no slash), try PATH
    if os.path.basename(p) == p:
        found = shutil.which(p)
        return found if found else None

    # Else verify file exists & is executable
    if os.path.isfile(p) and os.access(p, os.X_OK):
        return p
    return None

def explain_exec_problem(label: str, want_path: str):
    msg = [red_error(f"\n[{label}] Cannot execute: {want_path}")]
    abs_path = _expand_abs(want_path)

    # Specific hints
    if not os.path.exists(abs_path):
        msg.append("[!] File not found. Check daemons.json paths")
    else:
        if not os.access(abs_path, os.X_OK):
            msg.append("[!] File exists but is not executable (chmod +x).")
        # GVFS / noexec hint
        mount_note = ""
        try:
            if _is_gvfs_path(abs_path):
                mount_note = "[!] This appears to be a GVFS/FUSE mount; executing binaries here is often blocked (noexec)."
        except Exception:
            pass
        if mount_note:
            msg.append(f"[!] {mount_note} Copy the binary to a local filesystem (e.g., /usr/local/bin) and reference that path.")

    msg.append("[!] Tip: use absolute paths, or put the binary in PATH and set just the program name in daemons.json.")
    print("\n".join(msg))


def get_local_version(cli_path, cli_args, field, data_dir):
    info = getinfo(cli_path, data_dir, cli_args)
    if "error" in info:
        print(red_error(f"Error getting local version: {info['error']}"))
        return None
    return info.get(field)

def get_remote_version(api_url, field):
    try:
        resp = requests.get(api_url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return data.get(field), data.get("html_url") 
    except Exception as e:
        print(f"Error fetching remote version: {e}")
        return None, None

def normalize_version(v):
    """Return a string version, handling ints and raw values from RPC."""
    if v is None:
        return ""
    v = str(v).strip()
    if v.startswith("v"):
        return v[1:]
    match = re.search(r"(\d+\.\d+\.\d+(-\d+)?)", v)
    return match.group(1) if match else v

class VersionCheckStyle(Style):
    default_style = ""
    styles = {
        Token.Generic.Heading: "bold ansiyellow",
        Token.Generic.Error: "bold ansired",
        Token.Generic.Subheading: "ansicyan",
    }

formatter = Terminal256Formatter(style=VersionCheckStyle)

def highlight_text(text, token_type):
    """Format a string using the specified token type and custom style."""
    out = StringIO()
    formatter.format([(token_type, text)], out)
    return out.getvalue().strip()


def check_versions(daemon_config):
    cli_ver_raw = get_local_version(
        daemon_config["cli_path"],
        daemon_config.get("cli_args", []),
        daemon_config["version_check"]["cli_field"],
        daemon_config["data_dir"]
    )
    remote_ver_raw, html_url = get_remote_version(
        daemon_config["version_check"]["github_api"],
        daemon_config["version_check"]["version_field"]
    )

    cli_ver = normalize_version(cli_ver_raw)
    remote_ver = normalize_version(remote_ver_raw)

    if not cli_ver or not remote_ver:
        print("Could not determine version(s).")
        print(f"GitHub version: {remote_ver}")
        print(f"Local version: {cli_ver}")
        print("\n\n")
        return

    try:
        local_version = parse_version(cli_ver)
        remote_version = parse_version(remote_ver)

        if local_version == remote_version:
            print("Version check: Up to date")
        elif local_version < remote_version:
            print(highlight_text("Version check: Version mismatch", Token.Generic.Heading))
            print(f"GitHub version: {remote_ver}")
            print(f"Local version: {highlight_text(cli_ver, Token.Generic.Error)}")
            if html_url:
                print(f"Download new version: {html_url}")
        else:
            print("Version check: Local version is newer than GitHub")
            print(f"GitHub version: {remote_ver}")
            print(f"Local version: {cli_ver}")
    except Exception as e:
        print("Version check: Unable to parse versions")
        print(f"GitHub version: {remote_ver}")
        print(f"Local version: {cli_ver}")
        print(f"Error: {e}")
    
    print("\n") 

def getinfo(cli_path, data_dir, cli_args):
    """Runs getinfo command to check if the daemon is running."""
    try:
        result = subprocess.run([cli_path, f"-datadir={data_dir}"] + cli_args + ["getinfo"], capture_output=True, text=True)
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return {"error": result.stderr.strip()}
    except Exception as e:
        return {"error": str(e)}

def get_log_file_position(data_dir):
    """Gets the current position of the debug.log file."""
    debug_log_path = os.path.join(data_dir, 'debug.log')
    try:
        with open(debug_log_path, 'r') as log_file:
            log_file.seek(0, os.SEEK_END)
            return log_file.tell()
    except FileNotFoundError:
        return 0

def read_debug_log(data_dir, last_position, last_message):
    """Reads new unique lines from the debug.log file, ignore timestamps and UpdateTip messages."""
    debug_log_path = os.path.join(data_dir, 'debug.log')
    new_lines = []
    try:
        with open(debug_log_path, 'r') as log_file:
            log_file.seek(last_position)
            for line in log_file:
                stripped_line = re.sub(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ', '', line).strip()
                if stripped_line.startswith("UpdateTip"):
                    continue  # Ignore UpdateTip messages
                if stripped_line != last_message:
                    new_lines.append(stripped_line)
                    last_message = stripped_line
            last_position = log_file.tell()
    except FileNotFoundError:
        new_lines.append("debug.log not found.")
    return new_lines, last_position, last_message

def preflight_paths(daemon):
    problems = False

    # Resolve CLI and daemon executables
    cli_abs = resolve_executable(daemon["cli_path"])
    if not cli_abs:
        explain_exec_problem(f"{daemon['name']} CLI", daemon["cli_path"])
        problems = True

    daemon_abs = resolve_executable(daemon["daemon_path"])
    if not daemon_abs:
        explain_exec_problem(f"{daemon['name']} daemon", daemon["daemon_path"])
        problems = True

    # Validate datadir (create it if missing is OK; but warn if on GVFS)
    data_dir = os.path.expanduser(daemon["data_dir"])
    if not os.path.isdir(data_dir):
        print(f"[{daemon['name']}] data_dir does not exist: {data_dir}")
        try:
            os.makedirs(data_dir, exist_ok=True)
            print(f"[{daemon['name']}] Created data_dir: {data_dir}")
        except Exception as e:
            print(f"[{daemon['name']}] Failed to create data_dir: {e}")
            problems = True

    if _is_gvfs_path(data_dir):
        print(f"[{daemon['name']}] Warning: data_dir is on a GVFS/FUSE mount ({data_dir}). That's fine for data, "
              "but do not place executables there (noexec mounts often block execution).")

    return (cli_abs, daemon_abs, data_dir, not problems)

def launch_daemon(daemon_name, daemon_path, data_dir, daemon_args):
    """Starts the daemon process"""
    abs_path = resolve_executable(daemon_path)
    if not abs_path:
        explain_exec_problem(f"{daemon_name} daemon", daemon_path)
        return False

    try:
        subprocess.Popen(
            [abs_path, f"-datadir={data_dir}"] + daemon_args + ["-daemon"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        print(f"[{daemon_name}] beep bop - initializing...")
        return True
    except FileNotFoundError:
        # (Shouldnt happen after resolve_executable)
        explain_exec_problem(f"{daemon_name} daemon", abs_path)
        return False
    except PermissionError as e:
        print(red_error(f"\n[{daemon_name}] Permission denied when executing {abs_path}: {e}"))
        print("[!] Ensure the file is executable (chmod +x) and not on a noexec mount.")
        return False
    except OSError as e:
        # Catch noexec 
        if e.errno in (errno.EACCES, getattr(errno, 'EPERM', -1)):
            print(red_error(f"\n[{daemon_name}] OS refused to execute {abs_path}: {e}"))
            print("[!] Likely a noexec mount (e.g., GVFS/FUSE). Move the binary to a local filesystem and try again.")
        else:
            print(f"[{daemon_name}] Failed to start daemon: {e}")
        return False


def monitor_startup(daemon_name, cli_path, data_dir, cli_args):
    """Monitors the daemon until it starts successfully."""
    last_error = None
    last_log_position = get_log_file_position(data_dir)  # Skip existing log entries
    last_message = None
    while True:
        info = getinfo(cli_path, data_dir, cli_args)
        if "error" in info:
            error_message = info["error"].split("error message:")[-1].strip()
            if "couldn't connect to server" in error_message:
                error_message = "starting RPC server"
            if error_message != last_error:
                print(f"[{daemon_name}] {error_message}")
                last_error = error_message

            # Read new unique lines from debug.log
            new_log_lines, last_log_position, last_message = read_debug_log(data_dir, last_log_position, last_message)
            for line in new_log_lines:
                print(f"[{daemon_name} startup] {line}")
            time.sleep(1)
        else:
            print(f"{daemon_name} daemon initialized - ready for RPC commands\n\n")
            return

def cli_interaction(cli_path, data_dir, cli_args, daemon_name):
    """Allows user to send commands to the daemon CLI."""
    while True:
        print(f"[{daemon_name.upper()}] Enter command (or 'exit' to quit):")
        cmd = input("→ ").strip()
        if cmd.lower() == "exit":
            break
        args = cmd.split()
        try:
            result = subprocess.run([cli_path, f"-datadir={data_dir}"] + cli_args + args, capture_output=True, text=True)
            output = result.stdout if result.returncode == 0 else result.stderr
            
            # Try to pretty-print JSON responses
            try:
                json_output = json.loads(output)
                formatted_json = json.dumps(json_output, indent=4)
                print(highlight(formatted_json, JsonLexer(), Terminal256Formatter(style="monokai")))
            except json.JSONDecodeError:
                print(output)
        except Exception as e:
            print(f"Error: {e}")

def main():
    print("Select a daemon to interact with:")
    for key, daemon in daemons.items():
        colored_key = highlight_text(f"{key}.", Token.Generic.Subheading)
        print(f"{colored_key} {daemon['name']}")

    choice = input("Enter number: ").strip()
    if choice not in daemons:
        print("Invalid selection.")
        return

    daemon = daemons[choice]
    daemon_name = daemon["name"]
    cli_path = daemon["cli_path"]
    daemon_path = daemon["daemon_path"]
    # Resolve/validate early
    cli_abs, daemon_abs, data_dir, ok = preflight_paths(daemon)
    if not ok:
        print(red_error(f"\n[{daemon_name}] Fix the issues above and run again.\n"))
        return

    cli_args = daemon.get("cli_args", [])
    daemon_args = daemon.get("daemon_args", [])

    info = getinfo(cli_abs, data_dir, cli_args)
    if "error" in info:
        print(f"{daemon_name} daemon, you there?")
        if not launch_daemon(daemon_name, daemon_abs, data_dir, daemon_args):
            # Launch failed... dont loop forever, show last error and stop
            return
        monitor_startup(daemon_name, cli_abs, data_dir, cli_args)
    else:
        print("Daemon is already running.")

    check_versions(daemon)
    cli_interaction(cli_abs, data_dir, cli_args, daemon_name)

    
if __name__ == "__main__":
    main()
