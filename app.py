import sys
import os
import json
import subprocess
import datetime
import shutil
import hashlib
import difflib

# ------------------ CONSTANTS ------------------

FOLDER_NAME = ".repoflow"
IGNORE_FILE = ".repoflowignore"

DEFAULT_IGNORES = [
    # --- Version Control ---
    ".git/", ".gitignore", ".gitmodules", ".hg/", ".svn/",

    # --- Node / Frontend ---
    "node_modules/", ".npm/", ".yarn/", ".pnpm-store/", ".next/", ".nuxt/", ".svelte-kit/", ".vite/", "dist/", "build/", "out/", ".vercel/", ".netlify/",

    # --- Python ---
    "__pycache__/", "*.pyc", "*.pyo", "*.pyd", ".venv/", "venv/", "env/", ".pytest_cache/", ".mypy_cache/",

    # --- Java / JVM ---
    "target/", ".gradle/", "*.class",

    # --- C / C++ / Rust / Go ---
    "*.o", "*.out", "*.exe", "*.dll", "*.so", "*.dylib", "*.a", "*.lib", "bin/", "obj/", "cargo.lock",

    # --- Environment & Secrets ---
    ".env", ".env.*", "*.pem", "*.key", "*.crt", "*.p12", "*.keystore",

    # --- Logs & Temp ---
    "*.log", "logs/", "tmp/", "temp/", ".cache/",

    # --- Databases ---
    "*.db", "*.sqlite", "*.sqlite3", "*.mdb", "*.dump",

    # --- IDEs & Editors ---
    ".idea/", ".vscode/", ".vs/", "*.swp", "*.swo", "*.bak",

    # --- OS Junk ---
    ".DS_Store", "Thumbs.db", "desktop.ini",

    # --- Testing / Coverage ---
    "coverage/", ".nyc_output/", "htmlcov/",

    # --- Repoflow internals ---
    ".repoflow/"
]


# ------------------ UTILS ------------------

def normalize(path: str) -> str:
    path = path.replace("\\", "/")
    if path.startswith("./"):
        path = path[2:]
    if path == ".":
        return ""
    return path


def hide_folder_windows(path):
    if not sys.platform.startswith("win"):
        return

    subprocess.run(["attrib", "+H", path], shell=True)

    for root, dirs, files in os.walk(path):
        for d in dirs:
            subprocess.run(["attrib", "+H", os.path.join(root, d)], shell=True)
        for f in files:
            subprocess.run(["attrib", "+H", os.path.join(root, f)], shell=True)


# ------------------ IGNORE SYSTEM ------------------

def load_ignore_rules(project_dir):
    ignore_path = os.path.join(project_dir, IGNORE_FILE)
    if not os.path.exists(ignore_path):
        return []
    with open(ignore_path, "r") as f:
        return [line.strip() for line in f if line.strip()]

def should_ignore(rel_path, ignore_rules):
    rel_path = normalize(rel_path)

    # 🔥 absolute hard rules
    if rel_path.startswith(".git/") or rel_path == ".git":
        return True
    if rel_path.startswith(".repoflow/") or rel_path == ".repoflow":
        return True

    name = os.path.basename(rel_path)

    for rule in ignore_rules:
        rule = normalize(rule)

        if rule.endswith("/") and rel_path.startswith(rule[:-1] + "/"):
            return True

        if rule.startswith("*") and name.endswith(rule[1:]):
            return True

        if rel_path == rule or name == rule:
            return True

    return False

# ------------------ FILE COLLECTION ------------------

def collect_files(project_dir):
    ignore_rules = load_ignore_rules(project_dir)
    included = []

    for root, dirs, files in os.walk(project_dir):
        rel_root = normalize(os.path.relpath(root, project_dir))
        if rel_root == ".":
            rel_root = ""

        dirs[:] = [
            d for d in dirs
            if not should_ignore(normalize(os.path.join(rel_root, d)), ignore_rules)
        ]

        if FOLDER_NAME in dirs:
            dirs.remove(FOLDER_NAME)

        for file in files:
            rel_path = normalize(os.path.join(rel_root, file))
            if not should_ignore(rel_path, ignore_rules):
                included.append(rel_path)

    return included

# ------------------ BASE SNAPSHOT ------------------

def copy_base_snapshot(project_dir, files):
    base_dir = os.path.join(project_dir, FOLDER_NAME, "commits", "base")

    for rel_path in files:
        src = os.path.join(project_dir, rel_path)
        dst = os.path.join(base_dir, rel_path)

        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)

# ------------------ INIT ------------------
def atomic_write_json(path, data):
    """
    Safely write JSON on Windows by using a temp file + replace.
    """
    tmp_path = path + ".tmp"

    # write to temp file first
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    # ensure old file is removable
    if os.path.exists(path):
        try:
            os.chmod(path, 0o666)
        except Exception:
            pass

    # atomic replace (Windows-safe)
    os.replace(tmp_path, path)

def init_repo(force=False):
    project_dir = os.getcwd()
    repo_path = os.path.join(project_dir, FOLDER_NAME)
    ignore_path = os.path.join(project_dir, IGNORE_FILE)

    if force and os.path.exists(repo_path):
        print("Reinitializing RepoFlow...")
        force_remove(repo_path)

    if force and os.path.exists(repo_path):
        shutil.rmtree(os.path.join(repo_path, "commits", "base"))
        os.makedirs(os.path.join(repo_path, "commits", "base"))
        print("Reinitializing RepoFlow...")

    if not os.path.exists(repo_path):
        os.makedirs(os.path.join(repo_path, "commits", "base"))
        os.makedirs(os.path.join(repo_path, "diffs"))

    if not os.path.exists(ignore_path):
        with open(ignore_path, "w") as f:
            f.write("\n".join(DEFAULT_IGNORES))

    files = collect_files(project_dir)
    copy_base_snapshot(project_dir, files)

    build_state(project_dir, files)

    metadata = {
        "project_dir": project_dir,
        "ignore_path": ignore_path,
        "version": "1.0",
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "files_included": files
    }

    with open(os.path.join(repo_path, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=4)

    with open(os.path.join(repo_path, "log.json"), "w") as f:
        json.dump([], f)

    with open(os.path.join(repo_path, "config.json"), "w") as f:
        json.dump({"version": "1.0"}, f)

    hide_folder_windows(repo_path)
    print("Repoflow initialized")

    hide_folder_windows(repo_path)

def load_state(project_dir):
    state_path = os.path.join(project_dir, ".repoflow", "state.json")
    if not os.path.exists(state_path):
        return {}
    with open(state_path, "r") as f:
        return json.load(f)

def status_repo():
    project_dir = os.getcwd()

    old_state = load_state(project_dir)
    current_files = collect_files(project_dir)

    current_state = {}
    for rel_path in current_files:
        abs_path = os.path.join(project_dir, rel_path)
        if os.path.isfile(abs_path):
            current_state[rel_path] = compute_file_hash(abs_path)

    added = []
    modified = []
    deleted = []

    for path, hash_val in current_state.items():
        if path not in old_state:
            added.append(path)
        elif old_state[path] != hash_val:
            modified.append(path)

    for path in old_state:
        if path not in current_state:
            deleted.append(path)

    if not added and not modified and not deleted:
        print("Working tree clean.")
        return

    print("\nChanges not committed:\n")

    if modified:
        print("Modified:")
        for f in modified:
            print(f"  {f}")

    if added:
        print("\nAdded:")
        for f in added:
            print(f"  {f}")

    if deleted:
        print("\nDeleted:")
        for f in deleted:
            print(f"  {f}")

# ------------------ DIFF (UNCHANGED) ------------------

def read_file(path):
    with open(path, "r") as f:
        lines = f.read().split("\n")
    return ["\n" if line == "" else line for line in lines]

def compute_file_hash(file_path, chunk_size=8192):
    """Return SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def build_state(project_dir, files_included):
    """
    Build state.json mapping:
    relative_path -> file_hash
    """
    state = {}

    for rel_path in files_included:
        abs_path = os.path.join(project_dir, rel_path)

        if not os.path.isfile(abs_path):
            continue

        file_hash = compute_file_hash(abs_path)
        state[rel_path] = file_hash

    state_path = os.path.join(project_dir, ".repoflow", "state.json")

    atomic_write_json(state_path, state)

    return state

def get_changes(project_dir):
    old_state = load_state(project_dir)
    current_files = collect_files(project_dir)

    current_state = {}
    for rel_path in current_files:
        abs_path = os.path.join(project_dir, rel_path)
        if os.path.isfile(abs_path):
            current_state[rel_path] = compute_file_hash(abs_path)

    added, modified, deleted = [], [], []

    for path, hash_val in current_state.items():
        if path not in old_state:
            added.append(path)
        elif old_state[path] != hash_val:
            modified.append(path)

    for path in old_state:
        if path not in current_state:
            deleted.append(path)

    return added, modified, deleted, current_state

def get_next_commit_id(repo_path):
    log_path = os.path.join(repo_path, "log.json")
    if not os.path.exists(log_path):
        return 1

    with open(log_path, "r") as f:
        log = json.load(f)

    return len(log) + 1

def save_commit_diff(repo_path, commit_id, added, modified, deleted):
    diff = {
        "added": added,
        "modified": modified,
        "deleted": deleted
    }

    diff_path = os.path.join(repo_path, "diffs", f"c{commit_id}.json")
    with open(diff_path, "w") as f:
        json.dump(diff, f, indent=4)

def read_lines(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.readlines()

def generate_diff(old_lines, new_lines, file_path):
    return difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm=""
    )


def update_head(project_dir, added, modified, deleted):
    head_dir = os.path.join(project_dir, ".repoflow", "commits", "head")
    base_dir = os.path.join(project_dir, ".repoflow", "commits", "base")

    # Create HEAD from base if missing
    if not os.path.exists(head_dir):
        shutil.copytree(base_dir, head_dir)

    # Handle added + modified files
    for path in added + modified:
        src = os.path.join(project_dir, path)
        dst = os.path.join(head_dir, path)

        os.makedirs(os.path.dirname(dst), exist_ok=True)

        # 🔐 Windows-safe overwrite
        if os.path.exists(dst):
            try:
                os.remove(dst)
            except PermissionError:
                print(f"⚠ Skipped locked file (HEAD not updated): {path}")
                continue

        try:
            shutil.copy2(src, dst)
        except PermissionError:
            print(f"⚠ Skipped locked file (HEAD not updated): {path}")

    # Handle deleted files
    for path in deleted:
        target = os.path.join(head_dir, path)

        if os.path.isfile(target):
            try:
                os.remove(target)
            except PermissionError:
                print(f"⚠ Could not delete locked file from HEAD: {path}")
                continue

            # Cleanup empty parent dirs
            parent = os.path.dirname(target)
            while (
                parent
                and parent != head_dir
                and os.path.isdir(parent)
                and not os.listdir(parent)
            ):
                os.rmdir(parent)
                parent = os.path.dirname(parent)

def force_remove(path):
    def onerror(func, p, exc):
        try:
            os.chmod(p, 0o777)  # remove read-only
            func(p)
        except Exception:
            print(f"⚠ Could not remove locked file: {p}")

    if os.path.exists(path):
        shutil.rmtree(path, onerror=onerror)

def diff_file(rel_path):
    project_dir = os.getcwd()
    rel_path = normalize(rel_path)
    head_root = os.path.join(project_dir, ".repoflow", "commits", "head")
    if not os.path.exists(head_root):
        print("No commits yet. Nothing to diff against.")
        return

    head_path = os.path.join(project_dir, ".repoflow", "commits", "head", rel_path)
    work_path = os.path.join(project_dir, rel_path)

    head_exists = os.path.isfile(head_path)
    work_exists = os.path.isfile(work_path)

    if not head_exists and not work_exists:
        print("File not found in HEAD or working tree.")
        return

    old_lines = read_lines(head_path) if head_exists else []
    new_lines = read_lines(work_path) if work_exists else []

    diff = generate_diff(old_lines, new_lines, rel_path)

    printed = False
    for line in diff:
        printed = True
        print(line)

    if not printed:
        print("No differences.")

def update_log(repo_path, commit_id, message, added, modified, deleted):
    log_path = os.path.join(repo_path, "log.json")

    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            log = json.load(f)
    else:
        log = []

    log.append({
        "id": commit_id,
        "timestamp": datetime.datetime.now().isoformat(),
        "message": message,
        "changes": {
            "added": added,
            "modified": modified,
            "deleted": deleted
        }
    })

    atomic_write_json(log_path, log)

def save_state(project_dir, state):
    state_path = os.path.join(project_dir, ".repoflow", "state.json")
    atomic_write_json(state_path, state)

def commit_repo(message="Commit"):
    project_dir = os.getcwd()
    repo_path = os.path.join(project_dir, ".repoflow")

    added, modified, deleted, current_state = get_changes(project_dir)

    if not added and not modified and not deleted:
        print("Nothing to commit.")
        return

    commit_id = get_next_commit_id(repo_path)

    save_commit_diff(repo_path, commit_id, added, modified, deleted)
    update_head(project_dir, added, modified, deleted)
    save_state(project_dir, current_state)
    update_log(repo_path, commit_id, message, added, modified, deleted)

    print(f"Committed as c{commit_id}")
    print(f"  Added: {len(added)}")
    print(f"  Modified: {len(modified)}")
    print(f"  Deleted: {len(deleted)}")

def log_repo():
    project_dir = os.getcwd()
    repo_path = os.path.join(project_dir, ".repoflow")
    log_path = os.path.join(repo_path, "log.json")

    if not os.path.exists(log_path):
        print("No Commits yet")
        return

    with open(log_path, "r") as f:
        log = json.load(f)

    if not log:
        print("No Commits yet")
        return

    for commit in reversed(log):
        print(f"commit c{commit['id']}")
        print(f"Date: {commit['timestamp']}")
        print()
        print(f"    {commit['message']}")
        print()

        changes = commit["changes"]

        if changes.get("added"):
            print("    Added:")
            for f in changes["added"]:
                print(f"      {f}")

        if changes.get("modified"):
            print("    Modified:")
            for f in changes["modified"]:
                print(f"      {f}")

        if changes.get("deleted"):
            print("    Deleted:")
            for f in changes["deleted"]:
                print(f"      {f}")

        print("-" * 40)

def ensure_restore_safe(project_dir):
    repo_path = os.path.join(project_dir, ".repoflow")
    head_path = os.path.join(project_dir, ".repoflow", "commits", "head")

    if not os.path.exists(repo_path):
        print("Repoflow not Initialized yet")
        return False

    if not os.path.exists(head_path):
        print("No commits yet, nothing to restore")
        return False

    return True

def collect_tracked_files(project_dir):
    state_path = os.path.join(project_dir, ".repoflow", "state.json")

    if not os.path.exists(state_path):
        print("State file missing. Cannot restore.")
        return None

    try:
        with open(state_path, "r") as f:
            state = json.load(f)
    except Exception:
        print("State file is corrupted. Cannot restore.")
        return None

    return list(state.keys())

def cleanup_working_tree(project_dir):
    """
    Remove ONLY tracked files.
    Never touch .git, .repoflow, or ignored paths.
    """
    state_path = os.path.join(project_dir, ".repoflow", "state.json")

    if not os.path.exists(state_path):
        print("State file missing. Cannot cleanup.")
        return

    with open(state_path, "r", encoding="utf-8") as f:
        state = json.load(f)

    ignore_rules = load_ignore_rules(project_dir)

    for rel_path in state.keys():
        rel_path = normalize(rel_path)

        # 🚫 hard safety checks
        if rel_path.startswith(".git/"):
            continue
        if rel_path.startswith(".repoflow/"):
            continue
        if should_ignore(rel_path, ignore_rules):
            continue

        abs_path = os.path.join(project_dir, rel_path)

        try:
            if os.path.isfile(abs_path):
                os.remove(abs_path)

                # cleanup empty parents
                parent = os.path.dirname(abs_path)
                while (
                    parent
                    and parent != project_dir
                    and os.path.isdir(parent)
                    and not os.listdir(parent)
                ):
                    os.rmdir(parent)
                    parent = os.path.dirname(parent)

        except PermissionError:
            print(f"⚠ Skipped locked file: {rel_path}")

def restore_head_snapshot(project_dir):
    head_dir = os.path.join(project_dir, ".repoflow", "commits", "head")

    if not os.path.exists(head_dir):
        print("No HEAD snapshot found.")
        return

    for root, _, files in os.walk(head_dir):
        rel_root = normalize(os.path.relpath(root, head_dir))
        if rel_root == ".":
            rel_root = ""

        for file in files:
            src = os.path.join(root, file)
            dst = os.path.join(project_dir, rel_root, file)

            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)

def restore_base_snapshot(project_dir):
    base_dir = os.path.join(project_dir, ".repoflow", "commits", "base")
    ignore_rules = load_ignore_rules(project_dir)

    if not os.path.exists(base_dir):
        print("Base snapshot missing.")
        return

    for root, dirs, files in os.walk(base_dir):
        rel_root = normalize(os.path.relpath(root, base_dir))
        if rel_root == ".":
            rel_root = ""

        # 🚫 prune ignored directories
        dirs[:] = [
            d for d in dirs
            if not should_ignore(normalize(os.path.join(rel_root, d)), ignore_rules)
        ]

        for file in files:
            rel_path = normalize(os.path.join(rel_root, file))

            if should_ignore(rel_path, ignore_rules):
                continue

            src = os.path.join(root, file)
            dst = os.path.join(project_dir, rel_path)

            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)

def apply_diff(project_dir, commit_id):
    """
    Apply diff cN.json to working tree.
    For v1: only DELETIONS are applied.
    Base snapshot already contains full file content.
    """
    repo_path = os.path.join(project_dir, ".repoflow")
    diff_path = os.path.join(repo_path, "diffs", f"c{commit_id}.json")

    if not os.path.exists(diff_path):
        print(f"Diff c{commit_id} not found.")
        return

    with open(diff_path, "r") as f:
        diff = json.load(f)

    for rel_path in diff.get("deleted", []):
        rel_path = normalize(rel_path)
        abs_path = os.path.join(project_dir, rel_path)

        if os.path.isfile(abs_path):
            os.remove(abs_path)

            parent = os.path.dirname(abs_path)
            while (
                parent
                and parent != project_dir
                and os.path.isdir(parent)
                and not os.listdir(parent)
            ):
                os.rmdir(parent)
                parent = os.path.dirname(parent)

def rebuild_state_from_working_tree(project_dir):
    files = collect_files(project_dir)
    state = {}

    for rel_path in files:
        abs_path = os.path.join(project_dir, rel_path)
        if os.path.isfile(abs_path):
            state[rel_path] = compute_file_hash(abs_path)

    save_state(project_dir, state)

def restore_to_commit(project_dir, target_commit):
    repo_path = os.path.join(project_dir, ".repoflow")
    base_dir = os.path.join(repo_path, "commits", "base")

    if not os.path.exists(base_dir):
        print("Base snapshot missing. Cannot restore.")
        return

    cleanup_working_tree(project_dir)

    restore_base_snapshot(project_dir)

    for commit_id in range(1, target_commit + 1):
        apply_diff(project_dir, commit_id)

    rebuild_state_from_working_tree(project_dir)

    reset_head_from_working_tree(project_dir)

    print(f"✔ Restored to commit c{target_commit}")


def reset_head_from_working_tree(project_dir):
    """
    Rebuild HEAD snapshot from working tree.
    Uses collect_files() so ignored files are NOT tracked.
    """
    head_dir = os.path.join(project_dir, ".repoflow", "commits", "head")

    if os.path.exists(head_dir):
        shutil.rmtree(head_dir)

    files = collect_files(project_dir)

    for rel_path in files:
        src = os.path.join(project_dir, rel_path)
        dst = os.path.join(head_dir, rel_path)

        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)

def validate_commit(repo_path, commit_id):
    log_path = os.path.join(repo_path, "log.json")

    if not os.path.exists(log_path):
        print("No commits found.")
        return False

    with open(log_path, "r") as f:
        log = json.load(f)

    try:
        cid = int(commit_id.lstrip("c"))
    except ValueError:
        print("Invalid commit id format.")
        return False

    if cid < 1 or cid > len(log):
        print("Commit does not exist.")
        return False

    return cid

def restore_base(project_dir):
    base_dir = os.path.join(project_dir, ".repoflow", "commits", "base")

    for root, _, files in os.walk(base_dir):
        for file in files:
            src = os.path.join(root, file)
            rel = os.path.relpath(src, base_dir)
            dst = os.path.join(project_dir, rel)

            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)

def restore_repo(commit_id, force=False):
    project_dir = os.getcwd()
    repo_path = os.path.join(project_dir, ".repoflow")

    cid = validate_commit(repo_path, commit_id)
    if not cid:
        return

    if not force:
        print("⚠ This will discard current changes.")
        if input("Proceed? (y/N): ").lower() != "y":
            print("Restore aborted.")
            return

    restore_to_commit(project_dir, cid)

def unhide_windows(path):
    if not sys.platform.startswith("win"):
        return
    subprocess.run(["attrib", "-H", path], shell=True)

def destroy_repo():
    project_dir = os.getcwd()

    repo_path = os.path.join(project_dir, FOLDER_NAME)
    ignore_path = os.path.join(project_dir, IGNORE_FILE)

    if not os.path.exists(repo_path) and not os.path.exists(ignore_path):
        print("Repoflow not initialized.")
        return

    if os.path.exists(repo_path):
        unhide_windows(repo_path)

        for root, dirs, files in os.walk(repo_path):
            for d in dirs:
                unhide_windows(os.path.join(root, d))
            for f in files:
                unhide_windows(os.path.join(root, f))

        shutil.rmtree(repo_path)

    if os.path.exists(ignore_path):
        unhide_windows(ignore_path)
        os.remove(ignore_path)

    print("✔ Repoflow removed (unsynced successfully)")

def main():
    if len(sys.argv) < 2:
        print("Usage: repoflow <command>")
        return

    command = sys.argv[1]
    force = "--force" in sys.argv

    if command == "init":
        init_repo(force)
    elif command == "commit":
        commit_repo()
    elif command == "status":
        status_repo()
    elif command == "log":
        log_repo()
    elif command == "diff":
        if len(sys.argv) < 3:
            print("Usage: repoflow diff <file>")
            return
        diff_file(sys.argv[2])
    elif command == "restore":
        if len(sys.argv) < 3:
            print("Usage: repoflow restore <commit_id>")
            return

        commit_id = sys.argv[2]
        force = "--force" in sys.argv

        restore_repo(commit_id, force)
    elif command == "destroy":
        destroy_repo()
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()