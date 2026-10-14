# Configuration and Environment Files

## Local configuration

Copy the project-root `.env.example` to `.env` and edit the values for the
machine. The backend and Discord bot load this file at startup using
`python-dotenv`; existing process environment variables take precedence over
values in `.env`. Restart the relevant process after changing configuration.
The root `.env` is ignored by Git. Commit only `.env.example`, and never put
real credentials in it.

The Windows launcher scripts still pass their llama.cpp device and port
options directly to the server. On Windows, keep those launch options in
sync with `LLAMA_CPP_DEVICE`, `LLAMA_CPP_GPU_LAYERS`, and
`LLAMA_CPP_CTX_SIZE` when using the dashboard to switch models.

## Variables

| Variable | Default / purpose |
| --- | --- |
| `AI_SERVER_MODEL_DIR` | GGUF directory; defaults to `%LOCALAPPDATA%\AI-Server\models` on Windows or `~/AI-Server/models` elsewhere. |
| `LLAMA_SERVER_EXECUTABLE` | llama.cpp server binary; Windows uses the local Vulkan build path, while other systems search for `llama-server` on `PATH`. |
| `LLAMA_CPP_BASE_URL` | Local llama.cpp HTTP endpoint; defaults to `http://127.0.0.1:8080`. Keep this loopback-only when co-located with the backend. |
| `LLAMA_CPP_DEVICE` | GPU device passed during a model switch; defaults to `Vulkan0` on Windows and `ROCm0` elsewhere. Confirm the identifier against the actual build. |
| `LLAMA_CPP_GPU_LAYERS` | Number of model layers to offload during a model switch; defaults to `99`. |
| `LLAMA_CPP_CTX_SIZE` | Context size during a model switch; defaults to `4096`. |
| `SEARXNG_BASE_URL` | Optional SearXNG endpoint; defaults to `http://127.0.0.1:8888`. |
| `DISCORD_TOKEN` | Discord application's bot login credential. Required to connect the bot to Discord; never commit it. |
| `AI_SERVER_API_BASE` | API base URL used by the Discord bot; defaults to `http://127.0.0.1:8000`. |
| `LLAMA_CPP_TIMEOUT_SECONDS` | Timeout for llama.cpp chat requests; defaults to `120`. |
| `AI_SERVER_MAX_TOKENS` | Maximum tokens generated per chat reply; defaults to `256`. |
| `AI_SERVER_MAX_CHAT_CHARS` | Maximum characters accepted per streamed chat message; defaults to `4000`. |
| `AI_SERVER_CORS_ORIGINS` | Comma-separated browser origins allowed to call the API and open `/ws/chat`; defaults to `http://127.0.0.1:8001,http://localhost:8001`. `*` is rejected. Add the dashboard's origin here before serving it from another host. |
| `AI_SERVER_AUTH_DB_PATH` | SQLite authentication database; defaults to `%LOCALAPPDATA%\AI-Server\data\auth.sqlite3` on Windows or `~/AI-Server/data/auth.sqlite3` elsewhere. Protect this file and its directory. |
| `AI_SERVER_MEMORY_DB_PATH` | SQLite dashboard memory; defaults to `memory.sqlite3` beside the authentication database. Protect it and its directory; it contains private saved conversations/research citations and explicitly published admin-shared operational notes. |
| `AI_SERVER_AUTH_COOKIE_SECURE` | `true` by default; use Secure session cookies for HTTPS. Set `false` only for isolated loopback HTTP development; never expose that setup to a network. |
| `PROXMOX_API_URL` | Optional Proxmox API origin, such as `https://proxmox.example:8006`; required only for Proxmox-provider login. TLS verification is always enabled. |
| `AI_SERVER_BOT_API_TOKEN` | Separate shared high-entropy bearer credential (at least 32 characters) for bot-to-backend API requests. Set the same random value for backend and bot; do not reuse `DISCORD_TOKEN` or commit it. |
| `AI_SERVER_LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`; defaults to `INFO`. |
| `AI_SERVER_LOG_DIR` | Backend log directory; defaults to `%LOCALAPPDATA%\AI-Server\logs` on Windows or `~/AI-Server/logs` elsewhere. |
| `AI_SERVER_LOG_MAX_BYTES` / `AI_SERVER_LOG_BACKUP_COUNT` | Size of each `backend.log` file (default 5,000,000) and number of rotated files kept (default 5). |

Backend settings are validated once at startup by `ai-backend/config.py`.
A non-numeric or non-positive number, an unknown log level, or a wildcard CORS
origin stops startup with an error naming the variable. Blank values use the
default. Logs go to the console and a rotating `backend.log`; chat message
text is not logged, but dashboard conversations are persisted in the
memory database until the account owner deletes them. Admin-published shared
notes are stored separately in the same database. Discord bot requests are
not persisted as dashboard conversations and do not receive shared admin
context.

## Dashboard account setup

After installing backend dependencies, create the first administrator from a
local terminal on the backend host:

```powershell
Set-Location ai-backend
python auth_admin.py create-user --username admin --role admin
```

The CLI prompts for the password without echoing it. It reads `.env` before
resolving the authentication database path. Use `reset-password`,
`create-user`, `set-role`, `disable-user`, `enable-user`, and `list-users` for
local account administration. For example:

```powershell
python auth_admin.py map-proxmox --username user@realm --role operator
python auth_admin.py unmap-proxmox --username user@realm
```

Roles are `admin`, `operator`, and `viewer`; at least one enabled local
administrator must remain.

To run the optional Discord bot, configure **both** credentials in the
ignored project-root `.env`:

- `DISCORD_TOKEN` is issued by Discord and lets the bot log in to Discord.
- `AI_SERVER_BOT_API_TOKEN` is a separate random secret of at least 32
  characters, shared by the bot and backend to authenticate bot API requests.
  Generate one in PowerShell with:

  ```powershell
  $bytes = New-Object byte[] 48
  $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
  $rng.GetBytes($bytes)
  [Convert]::ToBase64String($bytes)
  $rng.Dispose()
  ```

  Copy the generated value to `AI_SERVER_BOT_API_TOKEN` in `.env`. Do not use
  your Discord token for this setting or expose the backend token to browser
  code. Process-level environment variables override `.env`, so if the bot
  still reports this setting missing, check and clear any stale value in the
  current PowerShell session with
  `Remove-Item Env:AI_SERVER_BOT_API_TOKEN -ErrorAction SilentlyContinue`,
  then start the bot again.

The Discord bot is optional. On Windows, `setup-windows.bat` installs its
dependencies and `run-discord-bot.bat` starts it. Slash commands require the
bot to be invited to the intended server with the `applications.commands`
scope and permissions appropriate for responding there. To let the bot answer
direct mentions such as `@Krazy-AI how can you help?`, enable **Message Content
Intent** in the Discord Developer Portal under **Bot → Privileged Gateway
Intents**. The bot also enables this intent in code. It ignores messages from
bots and responds only when directly mentioned; ordinary channel messages do
not trigger AI requests. Keep the bot's server permissions limited to the
channels where it should respond.

The dashboard connects to the backend on port 8000 when served locally from
port 8001, and otherwise uses its own origin by default. A deployment can set
`window.AI_SERVER_API_BASE` before `js/app.js` loads when it needs a different
API origin. The server-side variables do not set this browser value. LAN
access requires HTTPS, a reachable API/proxy configuration, and security
hardening first. See the [Linux/Proxmox transition runbook](./linux-proxmox-transition.md).

## `.gitignore` coverage

The repository `.gitignore` excludes local `.env` files (while allowing
`.env.example`), SQLite auth databases, Python environments and caches, test
output, downloaded model weights, logs, build artifacts, and common editor/OS
files. Keep model weights, credentials, and machine-specific generated files
out of source control.

Use `git check-ignore` to verify custom paths when changing the authentication
database location. Ignore rules do not remove files that are already tracked
by Git.
