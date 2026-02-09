import os
import sys
import time
import subprocess

# Configuration
POLL_INTERVAL = 1.0  # Seconds

def get_git_state():
    """
    Returns a tuple (commit_sha, branch_name) representing the current git state.
    Returns (None, None) if not in a git repo or error.
    """
    try:
        # Get current commit SHA
        commit = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], 
            stderr=subprocess.DEVNULL
        ).decode().strip()
        
        # Get current branch name (might fail if detached HEAD)
        try:
            branch = subprocess.check_output(
                ['git', 'symbolic-ref', '--short', 'HEAD'], 
                stderr=subprocess.DEVNULL
            ).decode().strip()
        except subprocess.CalledProcessError:
            branch = "HEAD (detached)"
            
        return commit, branch
    except Exception:
        return None, None

def start_bot():
    """
    Starts the bot as a subprocess.
    """
    # Use the current python interpreter
    cmd = [sys.executable, 'main.py']
    
    # Set environment variable to indicate local dev if needed
    env = os.environ.copy()
    
    print(f"🚀 [DevRunner] Starting bot...")
    return subprocess.Popen(cmd, env=env)

def main():
    print(f"👀 [DevRunner] Watching for GIT changes (Branch/Commit)...")
    
    current_commit, current_branch = get_git_state()
    if not current_commit:
        print("⚠️ [DevRunner] Not a git repository or git error. Auto-restart disabled.")
    else:
        print(f"📌 [DevRunner] Current: {current_branch} ({current_commit[:7]})")

    process = start_bot()
    
    try:
        while True:
            time.sleep(POLL_INTERVAL)
            
            new_commit, new_branch = get_git_state()
            
            if new_commit and (new_commit != current_commit or new_branch != current_branch):
                print(f"\n🔄 [DevRunner] Git change detected!")
                print(f"   From: {current_branch} ({current_commit[:7] if current_commit else '?'})")
                print(f"   To:   {new_branch} ({new_commit[:7]})")
                
                print("♻️ [DevRunner] Restarting bot...")
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                
                process = start_bot()
                current_commit, current_branch = new_commit, new_branch

            # Handle case where process crashed/exited on its own
            if process.poll() is not None:
                # We don't auto-restart on crash in this mode, unless git changes. 
                # Or we could, but user specifically asked for "restart only when...", assuming for code changes.
                # If it crashes, user probably sees the error and fixes it, then commits or manually restarts?
                # Let's keep it running and checking for git changes even if bot is dead.
                pass

    except KeyboardInterrupt:
        print("\n🛑 [DevRunner] Stopping...")
        if process.poll() is None:
            process.terminate()
            process.wait()

if __name__ == "__main__":
    main()
