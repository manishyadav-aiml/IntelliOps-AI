"""Dataset acquisition helper. NEVER called by the application; run it manually.

LogHub repo: https://github.com/logpai/loghub.git (small 2k-line samples per system).
The full HDFS_v1 / BGL archives are large and linked from the LogHub README (Zenodo); download them
manually and respect the licence/usage terms stated there. See docs/DATASET_GUIDE.md.

Usage:
    python scripts/download_dataset.py            # prints instructions only
    python scripts/download_dataset.py --clone    # shallow-clones the LogHub repo into data/raw/loghub
"""

import argparse
import subprocess
import sys
from pathlib import Path

REPO = "https://github.com/logpai/loghub.git"
TARGET = Path(__file__).resolve().parent.parent / "data" / "raw" / "loghub"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--clone", action="store_true", help="git clone --depth 1 the LogHub repository")
    args = parser.parse_args()
    if not args.clone:
        print(__doc__)
        return 0
    if TARGET.exists():
        print(f"{TARGET} already exists; nothing to do.")
        return 0
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.call(["git", "clone", "--depth", "1", REPO, str(TARGET)])


if __name__ == "__main__":
    sys.exit(main())
