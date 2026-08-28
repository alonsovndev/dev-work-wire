# Configuration

DevWorkWire uses a three-tier configuration system:

1. **`.env` file** — environment variables for secrets (never committed)
2. **`config_{env}.yml`** — structured settings (logging, Jira connection) loaded based on `APP_ENV`
3. **`devworkwire.yml`** — per-project provider config (provider selection, project key, field mappings)

## Environment Variables (`.env`)

Create a `.env` file in the project root. Start from the template:

```bash
cp .env.example .env
```

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `APP_ENV` | Environment name, selects the YAML config file | `local` |
| `JIRA_BASE_URL` | Your Jira instance URL | `https://your-domain.atlassian.net` |
| `JIRA_EMAIL` | Email associated with your Jira account | `you@example.com` |
| `JIRA_API_TOKEN` | API token from Atlassian | `ATATT3...` |

### How `APP_ENV` Works

The value of `APP_ENV` determines which YAML config file is loaded:

| `APP_ENV` | Config File Loaded | Use Case |
|-----------|-------------------|----------|
| `local` | `src/devworkwire/config/config_local.yml` | Local development |
| `test` | `src/devworkwire/config/config_test.yml` | Running tests |
| `dev` | `src/devworkwire/config/config_dev.yml` (create if needed) | Shared dev environment |
| `prod` | `src/devworkwire/config/config_prod.yml` (create if needed) | Production |

## YAML Configuration

The YAML files live in `src/devworkwire/config/` and provide structured settings. Here's what `config_local.yml` looks like:

```yaml
app:
  name: "DevWorkWire"
  version: "0.1.0"

logging:
  level: "debug"
  format_type: "text"
  console:
    enabled: true
    colored: true

jira:
  base_url: !ENV ${JIRA_BASE_URL}
  api_token: !ENV ${JIRA_API_TOKEN}
  email: !ENV ${JIRA_EMAIL}
  api_version: "3"
  timeout: 30
  max_retries: 3
```

### Logging Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `logging.level` | Log verbosity (`debug`, `info`, `warning`, `error`) | `info` |
| `logging.format_type` | Output format: `text` (plain, human-readable) or `json` (single-line structured) | `json` |

Use `format_type: "text"` for local and container runs so logs are easy to read. Use `format_type: "json"` for dev/prod so log aggregators can parse structured fields. Every record carries `request_id` and `user_id` correlation IDs, plus any `extra={...}` fields passed at the call site.

### Key Jira Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `jira.base_url` | Jira instance base URL | from `.env` |
| `jira.email` | Authentication email | from `.env` |
| `jira.api_token` | API token | from `.env` |
| `jira.api_version` | Jira REST API version | `3` |
| `jira.timeout` | Request timeout (seconds) | `30` |
| `jira.max_retries` | Max retry attempts on failure | `3` |
| `jira.rate_limit.requests_per_minute` | Rate limit threshold | `60` |

The `!ENV ${VAR_NAME}` syntax in YAML files pulls values from environment variables. This keeps secrets out of committed config files.

## Project Configuration (`devworkwire.yml`)

This file tells DevWorkWire which provider serves the project and the project key in that provider. Place it in the directory where you run `dwire` (or point to it with `dwire --config path/to/file.yml`).

Copy the example and adjust:

```bash
cp devworkwire.example.yml devworkwire.yml
```

```yaml
provider: jira
project_key: PROJ
field_mappings:
  story_points: customfield_10011
```

| Field | Description | Default |
|-------|-------------|---------|
| `provider` | Provider adapter to use (Phase 1: `jira` only) | **required** |
| `project_key` | Project key in the tracker for issue creation | **required** |
| `field_mappings.story_points` | Custom field ID for story points | `customfield_10011` |
| `transition_overrides` | Map DevWorkWire transition names to provider-specific names | `{}` |

## Generating a Jira API Token

1. Go to [Atlassian API tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click **Create API token**
3. Give it a label (e.g., "DevWorkWire")
4. Copy the token — you won't be able to see it again
5. Paste it into `.env` as `JIRA_API_TOKEN`

## Troubleshooting

**"Project configuration not found"**
→ Create a `devworkwire.yml` in the directory where you run `dwire`. Start from `devworkwire.example.yml`.

**"Configuration file not found"**
→ Check that `APP_ENV` matches an existing config file name. For `APP_ENV=local`, the file must be `config_local.yml`.

**"Jira API returned 401"**
→ Verify `JIRA_EMAIL` and `JIRA_API_TOKEN` are correct. Make sure the API token hasn't expired.

**"Unknown environment variable JIRA_BASE_URL"**
→ Ensure the `.env` file is in the project root and uses the correct variable names. Run `cat .env` to verify.
