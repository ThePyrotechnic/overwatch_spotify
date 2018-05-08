@echo off
echo Activating venv...
CALL venv\Scripts\activate.bat
echo Activated venv.
python overwatch_spotify.py -d 1
pause