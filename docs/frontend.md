# Frontend Documentation

## Structure

ai-dashboard/
    index.html
    css/style.css
    js/app.js

## Panels

- Chat Interface
- Models
- System Monitor
- Discord Bot
- Settings

## Key Features

- Internal scrolling chat window
- Fixed input bar
- Sidebar navigation
- Backend online/offline indicator
- Model cards discovered from installed GGUF files, with load status and file size
- Explicit web-research toggle and source links for research answers
- System monitor with animated bars
- Discord bot log viewer

## JavaScript Responsibilities

- Poll backend for telemetry
- Send chat messages
- Update UI panels
- Show the active model and list installed models; unloaded entries cannot be selected
- Display logs
- Manage theme/accent colors
