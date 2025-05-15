@echo off
echo Installing dependencies...
pip install -r requirements.txt
echo.
echo Creating cache directory...
if not exist "cache" mkdir cache
echo.
echo Starting News Scraper Application (Fixed Version)...
echo.
echo Press Ctrl+C to stop the server when done
echo.
python app.py
