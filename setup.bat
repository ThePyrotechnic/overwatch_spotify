@echo off

IF EXIST venv (
  echo A virtual environment already exists. Delete the "venv" folder to re-create it.
) ELSE (
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

pause
