# Repoflow – A Lightweight Version Control System (v1)

Repoflow is a **Git‑inspired version control system built from scratch in Python**.
It helps you understand how version control works internally by tracking file changes, creating commits, showing diffs, and restoring project state — **without using Git internally**.

This project is ideal for:

* Learning how VCS systems work
* System‑design interviews
* Demonstrating file‑system and tooling skills

---

## ✨ Features

* Initialize a repository (`repoflow init`)
* Track file changes (`repoflow status`)
* Create commits (`repoflow commit`)
* View commit history (`repoflow log`)
* Line‑level diffs (`repoflow diff <file>`)
* Restore project to an older commit (`repoflow restore cN`)
* Ignore system similar to `.gitignore`
* Safe file handling on Windows, macOS, and Linux

---

## ⚠️ Important v1 Limitations (Intentional)

Repoflow v1 is intentionally minimal and educational.

* Commits store **only metadata** (added / modified / deleted files)
* **File contents are NOT stored per commit**
* Restore works by:

  * Restoring the **base snapshot**
  * Replaying **deletions only**
* Files added after `init` **cannot be reconstructed** during restore

These limitations are **documented design decisions**, not bugs.
Future versions can extend this with blob storage or diffs.

---

## 📁 Project Structure

```
project/
├─ .repoflow/               # Repoflow internal data (hidden)
│  ├─ commits/
│  │  ├─ base/              # Base snapshot (initial files)
│  │  └─ head/              # Latest committed state
│  ├─ diffs/                # c1.json, c2.json ...
│  ├─ state.json            # Tracked file hashes
│  ├─ log.json              # Commit history
│  └─ config.json
│
├─ .repoflowignore          # Ignore rules
└─ your_project_files
```

---

## 🛠 Requirements

* Python **3.9+**
* Windows / macOS / Linux

Check Python version:

```bash
python --version
```

---

## 🔧 Setup as a Global Command

### ▶ Windows

1. Create a folder, for example:

   ```
   C:\repoflow\
   ```
2. Place `app.py` inside it and rename to `repoflow.py`
3. Add the folder to **PATH**:

   * Search **Environment Variables**
   * Edit **Path**
   * Add:

     ```
     C:\repoflow
     ```
4. Restart terminal

Run:

```bash
python repoflow.py init
```

(Optional) Create `repoflow.bat`:

```bat
@echo off
python C:\repoflow\repoflow.py %*
```

Then you can run:

```bash
repoflow init
```

---

### ▶ macOS / Linux

```bash
mv app.py repoflow
chmod +x repoflow
sudo mv repoflow /usr/local/bin/
```

Run:

```bash
repoflow init
```

---

## 🚀 Commands & Usage

### `repoflow init`

Initializes Repoflow in the current directory.

```bash
repoflow init
```

Output:

```
Repoflow initialized
```

---

### `repoflow status`

Shows uncommitted changes.

```bash
repoflow status
```

Example output:

```
Changes not committed:

Modified:
  app.py

Added:
  test.txt
```

If clean:

```
Working tree clean.
```

---

### `repoflow commit`

Creates a new commit.

```bash
repoflow commit
```

Output:

```
Committed as c1
  Added: 1
  Modified: 2
  Deleted: 0
```

> Commit messages are fixed in v1.
> Designed to support `-m` in v2.

---

### `repoflow log`

Displays commit history.

```bash
repoflow log
```

Output:

```
commit c2
Date: 2026-01-29T18:45:10

    Commit
----------------------------------------
commit c1
Date: 2026-01-29T18:40:02

    Commit
----------------------------------------
```

---

### `repoflow diff <file>`

Shows line‑level differences against last commit.

```bash
repoflow diff app.py
```

Output:

```diff
--- a/app.py
+++ b/app.py
@@ -12,6 +12,7 @@
+import difflib
```

---

### `repoflow restore cN`

Restores project to a previous commit.

```bash
repoflow restore c1
```

Prompt:

```
⚠ This will discard current changes.
Proceed? (y/N):
```

Success:

```
✔ Restored to commit c1
```

---

## 📄 Ignore Rules

Repoflow uses `.repoflowignore` similar to `.gitignore`.

Default ignores include:

* `.git/`, `.gitignore`
* `node_modules/`
* `.env`
* `.next/`, `.vercel/`
* `__pycache__/`
* IDE folders and build artifacts

---

## 🧠 Design Highlights

* No Git dependency
* Hash‑based change detection
* Explicit state management
* Permission‑safe file operations (Windows)
* Honest trade‑offs documented
* Clean separation of snapshots, state, and logs

---

## 🚧 Future Roadmap

* Commit messages
* File content blobs
* Delta‑based restore
* Branching
* Remote sync
* A Web Interface to do all the operations from interface

---

## ⭐ License

MIT License

---

Built for learning, clarity, and engineering honesty.
