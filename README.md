# Codex Collaboration Workspace

This repository is a file-based collaboration channel between two Codex agents:

- Mac Codex: the Codex running on this Mac.
- Windows Codex: the Codex running on the Windows computer.

The agents coordinate through Markdown files and shared artifacts. Each agent should pull before reading, update its own status, write requests or responses, then commit and push.

## Directory Layout

```text
inbox/
  to-mac.md          Messages and requests for Mac Codex.
  to-windows.md      Messages and requests for Windows Codex.
status/
  mac-status.md      Current status written by Mac Codex.
  windows-status.md  Current status written by Windows Codex.
artifacts/
  .gitkeep           Shared outputs, analysis files, datasets, screenshots.
logs/
  .gitkeep           Command logs or run notes worth sharing.
prompts/
  windows-startup-prompt.md
  mac-operating-prompt.md
```

## Collaboration Loop

Each Codex should use this loop:

```bash
git pull
# read inbox and status files
# do assigned work
# update status and response files
git add .
git commit -m "Update collaboration state"
git push
```

If there is a merge conflict, do not discard the other agent's changes. Resolve by preserving both useful updates.

## Message Rules

- Use `inbox/to-mac.md` only for messages addressed to Mac Codex.
- Use `inbox/to-windows.md` only for messages addressed to Windows Codex.
- Put durable outputs in `artifacts/`.
- Put large or noisy command output in `logs/`, then summarize it in status.
- Keep status files current enough that the other agent can resume without asking the user.

