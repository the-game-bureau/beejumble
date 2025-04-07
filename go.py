# -------------------------------------------------------------------
# 🚀 BEE JUMBLE FULL PIPELINE
#
# Runs the complete Bee Jumble pipeline in order:
#   1. scraper.py   → Updates bees.xml
#   2. jumbler.py   → Updates jumbledbees.xml
#   3. poster.py    → Uploads jumbledbees.xml + index.htm via FTP
#
# Usage:
#   python go.py
# -------------------------------------------------------------------

import subprocess
import sys

def run_script(name):
    print(f"\n🔧 Running {name}...")
    result = subprocess.run([sys.executable, name])
    if result.returncode != 0:
        print(f"❌ Error: {name} exited with status {result.returncode}.")
        sys.exit(result.returncode)
    print(f"✅ Finished {name}.")

if __name__ == "__main__":
    run_script("scraper.py")
    run_script("jumbler.py")
    run_script("poster.py")
    print("\n🎉 All Bee Jumble tasks complete. Site is live and updated.")
