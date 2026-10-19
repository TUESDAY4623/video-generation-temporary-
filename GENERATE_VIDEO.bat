@echo off
setlocal
cd /d "%~dp0videoforge-backend"
python generate_video_clips.py %*
pause
