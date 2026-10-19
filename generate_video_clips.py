"""Root entrypoint wrapper for VideoForge Clip Engine."""

import os
import sys
from pathlib import Path

# Adjust paths to videoforge-backend
backend_dir = Path(__file__).resolve().parent / "videoforge-backend"
sys.path.insert(0, str(backend_dir))
os.chdir(str(backend_dir))

# Execute the backend generate_video_clips script
import generate_video_clips

if __name__ == "__main__":
    generate_video_clips.main()
