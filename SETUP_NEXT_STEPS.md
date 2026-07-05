# Setup Next Steps

The local collaboration repository is ready at:

```text
/Users/zhangtian/Downloads/recent_deconvolution_methods_package/codex_collab
```

## 1. Create A Private GitHub Repository

The GitHub repository for this workspace is:

```text
https://github.com/zt97152023-ai/CellMem.git
```

## 2. Push From Mac

```bash
cd /Users/zhangtian/Downloads/recent_deconvolution_methods_package/codex_collab
git push -u origin main
```

If push asks for GitHub credentials, authenticate this Mac first. The `origin` remote is already configured.

## 3. Clone On Windows

On Windows PowerShell:

```powershell
cd C:\Users\YOUR_WINDOWS_USERNAME\Documents
git clone https://github.com/zt97152023-ai/CellMem.git
cd CellMem
```

## 4. Start Windows Codex

Open the cloned repository in Windows Codex and paste the full prompt from:

```text
prompts/windows-startup-prompt.md
```

## 5. Normal Collaboration Cycle

Mac Codex and Windows Codex should both follow this loop:

```bash
git pull
# read inbox and status
# work
# update own status and message files
git add .
git commit -m "Update collaboration state"
git push
```
