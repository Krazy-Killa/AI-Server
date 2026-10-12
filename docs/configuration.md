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
| `DISCORD_TOKEN` | Optional Discord bot credential. Leave unset/empty until the bot is configured; never commit a real token. |
| `AI_SERVER_API_BASE` | API base URL used by the Discord bot; defaults to `http://127.0.0.1:8000`. |

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

The dashboard currently uses a fixed API URL in `js/app.js`; these server-side
variables do not configure the browser's API origin. LAN access requires a
reachable API/proxy configuration and security hardening first. See the
[Linux/Proxmox transition runbook](./linux-proxmox-transition.md).

## `.gitignore` coverage

The repository `.gitignore` excludes local `.env` files (while allowing
`.env.example`), Python environments and caches, test output, downloaded
model weights, logs, build artifacts, and common editor/OS files. Keep model
weights, credentials, and machine-specific generated files out of source
control.

The current working directory is not initialized as a Git repository, so
Git's actual ignore status still needs verification after `git init` or when
the project is cloned into a repository.
