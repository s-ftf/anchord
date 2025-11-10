# anchord ⚓️

A lightweight command-line tool to simplify working with cryptocurrency daemons, especially when you keep binaries and data directories in non-standard locations.

For when you want the CLI interaction (`getinfo`, `sendtoaddress`, etc.) but without the hassle of remembering where binaries or data folders are or manually including arguments with each command. 

Single input (select network), and automatically connects to running daemons (or starts if not already up). Checks that installed version matches most recent repo version on startup. Provides a CLI input. Makes JSON output easier to read with syntax highlighting.

---

## Why Use anchord?

If you:

- Store daemon binaries in custom folders
- Use multiple chains stored in different locations and manually including `-datadir=`
- Use PBaaS environments with `-chain=` or other cli arguments
- Want to quickly boot and interact with multiple nodes

---

## Installation

```bash
# Clone the repository
git clone https://github.com/s-ftf/anchord.git
cd anchord

# Set up virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate  

# Install requirements
pip install -r requirements.txt
```

---

## Configuration

Define your daemons in `daemons.json`

Use absolute paths to the binaries to run the script from anywhere, or relative paths from where the script is located as shown below. Alternatively, add the binary to PATH and include only the binary name in the cli/daemon path in the daemons.json

```json
{
  "1": {
    "name": "verus",
    "daemon_path": "binaries/verus-cli/verusd",
    "cli_path": "binaries/verus-cli/verus",
    "data_dir": "data/VRSC/",
    "daemon_args": ["-rpcallowip=127.0.0.1", "-bootstrap=2"],
    "cli_args": [],
    "version_check": {
	  "github_api": "https://api.github.com/repos/VerusCoin/VerusCoin/releases/latest",
	  "version_field": "tag_name",
	  "cli_field": "VRSCversion"
	}
  },
  "2": {
    "name": "vARRR",
    "daemon_path": "binaries/verus-cli/verusd",
    "cli_path": "binaries/verus-cli/verus",
    "data_dir": "data/verus/",
    "daemon_args": ["-rpcallowip=127.0.0.1", "-chain=varrr"],
    "cli_args": ["-chain=varrr"],
    "version_check": {
	  "github_api": "https://api.github.com/repos/VerusCoin/VerusCoin/releases/latest",
	  "version_field": "tag_name",
	  "cli_field": "VRSCversion"
	}
  },
  "3": {
    "name": "Pirate",
    "daemon_path": "pirate/pirated",
    "cli_path": "pirate/pirate-cli",
    "data_dir": "data/ARRR/",
    "daemon_args": ["-rpcallowip=127.0.0.1"],
    "cli_args": [],
    "version_check": {
	  "github_api": "https://api.github.com/repos/PirateNetwork/pirate/releases/latest",
	  "version_field": "tag_name",
	  "cli_field": "version"
	}
  }
}

```

You can add as many daemons as you like, each with its own binary, data path, and $args that will automatically be included with each  daemon/cli command.

---

## Usage

```bash
python3 anchord.py
```

You’ll get an interactive prompt like this:

```
Select a daemon to interact with:
1. verus
2. vARRR
3. Pirate

Enter number: 1
verus daemon, you there?
[VERUS] beep bop - initializing...
[VERUS] starting RPC server
[VERUS startup] init message: Loading block index...
[VERUS startup] init message: Loading wallet...
[VERUS startup] init message: Done loading
VERUS daemon initialized - ready for RPC commands
Version check: Version mismatch
GitHub version: 1.2.10
Local version: 1.2.9-5
Download new version: https://github.com/VerusCoin/VerusCoin/releases/tag/v1.2.10


[VERUS] Enter command (or 'exit' to quit):
→ getinfo
{
    "VRSCversion": "1.2.9-5",
    "version": 2000753,
    "protocolversion": 170010,
    ...
}

[VERUS] Enter command (or 'exit' to quit):
→ stop
VRSC server stopping

[VERUS] Enter command (or 'exit' to quit):
→ exit

```

You can enter any CLI command you'd normally run, and if it returns JSON, `anchord` will pretty-print it in color.

---

## Features

- Launch daemons with custom binary + data locations
- Reads debug.log and shows node output
- Pretty-printed JSON responses with [Pygments](https://pygments.org/)
- Automatically include arguments with commands (such as -datadir= or -chain=)
- Can run multiple instances 

---

## Requirements

- Python 3.7+
- `pygments` (installed via `requirements.txt`)

---

## 🏴‍☠️ Built for Developers

This is unsupported. Use at your own risk
