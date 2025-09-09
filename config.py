"""
Configuration settings for Advanced Portfolio Tracker Pro
"""

import os
from datetime import datetime

# Application Configuration
APP_NAME = "Advanced Portfolio Tracker Pro"
APP_VERSION = "2.0.0"
APP_DESCRIPTION = "Professional Portfolio Management System"

# Database Configuration
DATABASE_NAME = "portfolio_tracker_pro.db"

# Default Settings
DEFAULT_CURRENCY = "INR"
DEFAULT_CURRENCY_SYMBOL = "₹"
DEFAULT_RISK_PROFILE = "Moderate"

# Tax Configuration (India)
STCG_TAX_RATE = 0.15  # 15% for short term capital gains
LTCG_TAX_RATE = 0.10  # 10% for long term capital gains above 1 lakh
LTCG_EXEMPTION_LIMIT = 100000  # 1 lakh exemption for LTCG

# Performance Thresholds
CONCENTRATION_RISK_THRESHOLD = 25  # % of portfolio in single stock
DIVERSIFICATION_MIN_STOCKS = 8

# Default Initial Cash for New Clients
DEFAULT_INITIAL_CASH = 100000.0

# Application metadata
APP_METADATA = {
    "company_name": "Portfolio Pro Solutions",
    "website": "www.portfoliopro.com",
    "email": "support@portfoliopro.com",
    "phone": "+91-XXXXX-XXXXX"
}
