# Changelog
All notable changes to the **AI Command Interface** project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) principles.

---

## [Unreleased]
### Added
- Initial `/docs` folder with full project documentation.
- Architecture overview, API reference, frontend/backend docs, GPU plan, and roadmap.
- Complete README.md with project summary and development instructions.
- Stable CSS layout with fixed sidebar and scrollable chat window.
- Dashboard panels: Chat, Models, System Monitor, Discord Bot, Settings.
- Backend FastAPI stubs for system telemetry, chat, models, and bot endpoints.
- Discord bot stub with status and log streaming.
- Model cards with VRAM usage bars.
- System monitor with animated metric bars.
- Backend online/offline indicator.
- Theme and accent color swatches.

### Changed
- Refactored dashboard layout to use CSS Grid for stable header/sidebar/main structure.
- Improved chat panel overflow handling (internal scroll, fixed input bar).
- Updated documentation to be copy‑safe and Markdown‑stable.

### Fixed
- Sidebar overflow issue when chat window expanded.
- Broken documentation code blocks due to nested Markdown fences.
- Panel height inconsistencies across dashboard sections.

---

## [0.1.0] — Initial Commit
### Added
- Project structure:
  - `ai-backend/`
  - `ai-dashboard/`
  - `discord-bot/`
  - `docs/`
- Basic FastAPI backend with placeholder endpoints.
- Initial dashboard UI with navigation and panel structure.
- Basic Discord bot connection logic.
- Stub GPU and LLM modules for development without hardware dependency.

---

