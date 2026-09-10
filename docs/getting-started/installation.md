# Installation

## Prerequisites

- **Python 3.12+** — verify with `python --version`
- **A Jira account** with API access — you'll need an [API token](https://id.atlassian.com/manage-profile/security/api-tokens)
- **Git** — only for the from-source install

## Option A: Install from PyPI (recommended)

```bash
pipx install devworkwire
```

`pipx` installs DevWorkWire in an isolated environment and puts the `dwire` command on your PATH. Plain `pip install devworkwire` also works but shares your active environment.

Then configure your Jira credentials in a `.env` file in the directory where you run `dwire` (see [Configuration](configuration.md)) and start:

```bash
dwire
```

You should see the DevWorkWire welcome screen with an interactive menu.

## Option B: From source (development)

### 1. Clone the repository

```bash
git clone https://github.com/alonsovndev/devworkwire.git
cd devworkwire
```

### 2. Create and activate a virtual environment

#### macOS / Linux

```bash
python -m venv .venv
source .venv/bin/activate
```

#### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install in editable mode (runtime + dev dependencies)

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your Jira credentials. See [Configuration](configuration.md) for details on each variable.

### 5. Verify the installation

```bash
dwire
```

You should see the DevWorkWire welcome screen with an interactive menu.

If you see a `ModuleNotFoundError`, make sure your virtual environment is activated and the editable install completed.

## Next Steps

- [Configure your Jira connection](configuration.md)
- [Learn the CLI commands](../guides/cli-reference.md)
- [Prepare your first Markdown epic](../guides/markdown-format.md)
