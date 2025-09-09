#!/usr/bin/env python3
"""
Easy startup script for Advanced Portfolio Tracker Pro
"""

import sys
import subprocess
import os

def check_requirements():
    """Check if all required packages are installed"""
    try:
        import streamlit
        import pandas
        import plotly
        import yfinance
        import openpyxl
        import reportlab
        print("✅ All required packages are installed!")
        return True
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("Please install requirements: pip install -r requirements.txt")
        return False

def main():
    """Main startup function"""
    print("🚀 Starting Advanced Portfolio Tracker Pro...")
    print("=" * 50)

    # Check requirements
    if not check_requirements():
        sys.exit(1)

    # Start Streamlit app
    try:
        print("📊 Launching Portfolio Management System...")
        print("🌐 The application will open in your default browser")
        print("🛑 Press Ctrl+C to stop the application")
        print("=" * 50)

        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])
    except KeyboardInterrupt:
        print("\n👋 Portfolio Tracker stopped. Have a great day!")
    except Exception as e:
        print(f"❌ Error starting application: {e}")

if __name__ == "__main__":
    main()
