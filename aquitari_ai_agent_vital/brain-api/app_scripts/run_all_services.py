"""
run_all_services.py

This script starts all required components of the Aquitari agent project:
- main.py (core agent logic)
- app.py (API / web application layer)
- redis_feedback_graph_updater.py (Redis listener for knowledge graph updates)

It ensures all scripts run in parallel as separate processes. Paths are defined
relative to the project root, so the project runs correctly on any machine.
"""

import sys
import subprocess
from pathlib import Path

# ✅ Get the root folder of the project (move up from app_scripts if needed)
BASE_DIR = Path(__file__).resolve().parent

# ✅ Define paths relative to BASE_DIR
MAIN_PATH = BASE_DIR / "main.py"
APP_PATH = BASE_DIR / "app.py"
REDIS_UPDATER_PATH = BASE_DIR / "app_scripts" / "redis_feedback_graph_updater.py"

def run_script(path: Path):
    """Run a Python script as a separate process."""
    return subprocess.Popen([sys.executable, str(path)])

if __name__ == "__main__":
    print("🚀 Starting all services...")

    main_proc = run_script(MAIN_PATH)
    app_proc = run_script(APP_PATH)
    redis_proc = run_script(REDIS_UPDATER_PATH)

    print("✅ All services started (main.py, app.py, redis_feedback_graph_updater.py).")
    print("⚠️ Press CTRL+C to stop all services.")

    try:
        main_proc.wait()
        app_proc.wait()
        redis_proc.wait()
    except KeyboardInterrupt:
        print("\n🛑 Stopping all services...")
        main_proc.terminate()
        app_proc.terminate()
        redis_proc.terminate()