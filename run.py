#!/usr/bin/env python3
"""
EV Betting Project - Main Entry Point
Run this file to start the web server
"""

import sys
import os

# Add both the project root and Backend to Python path
project_root = os.path.abspath(os.path.dirname(__file__))
backend_path = os.path.join(project_root, 'Backend')

sys.path.insert(0, project_root)
sys.path.insert(0, backend_path)

# Now import app
from app import app

if __name__ == '__main__':
    print("""
    ====================================================
           EV Betting Dashboard                   
    ====================================================
    
    Starting server...
    URL: http://localhost:5001
    
    Press Ctrl+C to stop
    """)
    
    app.run(host='0.0.0.0', port=5001, debug=True)