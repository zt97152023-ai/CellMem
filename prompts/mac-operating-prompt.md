# Mac Codex Operating Prompt

Use this repository as the collaboration workspace with Windows Codex.

Before each collaboration pass:

```bash
git pull
```

Read:

```text
README.md
status/windows-status.md
inbox/to-mac.md
```

Write Mac state only to:

```text
status/mac-status.md
```

Write messages to Windows only to:

```text
inbox/to-windows.md
```

Place shared outputs in:

```text
artifacts/
logs/
```

After a pass:

```bash
git add .
git commit -m "Update Mac Codex collaboration state"
git push
```

