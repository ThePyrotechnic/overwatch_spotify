@echo off

IF NOT EXIST venv (
    echo Creating venv...
    python -m venv venv
    echo Created venv.
    echo Activating venv...
    CALL venv\Scripts\activate.bat
    echo Activated venv.
    echo Installing requirements...
    pip install -r requirements.txt
    echo Installation complete.
)
echo Activating venv...
CALL venv\Scripts\activate.bat
echo Activated venv.
python overwatch_spotify.py -d 1

pause
