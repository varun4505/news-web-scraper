import sys
import os
import subprocess

# Add the parent directory to the path so we can import from app.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create cache directory if it doesn't exist
cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)
    print("Created cache directory")

# Import the Flask app from our main app.py
from app import app

# This is required for Vercel serverless functions
app.debug = False

# Export the app variable for Vercel
if __name__ == "__main__":
    app.run()
