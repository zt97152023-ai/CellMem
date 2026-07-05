# Setup Next Steps

The local collaboration repository is ready at:

```text
/Users/zhangtian/Downloads/recent_deconvolution_methods_package/codex_collab
```

## 1. Create A Private GitHub Repository

Create an empty private repository on GitHub, for example:

```text
codex-collab
```

Do not initialize it with README, `.gitignore`, or license because this local repository already has files.

## 2. Push From Mac

Replace the URL with your real repository URL:

```bash
cd /Users/zhangtian/Downloads/recent_deconvolution_methods_package/codex_collab
git remote add origin https://github.com/YOUR_USERNAME/codex-collab.git
git push -u origin main
```

## 3. Clone On Windows

On Windows PowerShell:

```powershell
cd C:\Users\YOUR_WINDOWS_USERNAME\Documents
git clone https://github.com/YOUR_USERNAME/codex-collab.git
cd codex-collab
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

