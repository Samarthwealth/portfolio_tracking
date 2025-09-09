import pandas as pd
from datetime import datetime
import numpy as np

def process_excel_upload(uploaded_file):
    """Process uploaded Excel file and return standardized DataFrame"""
    try:
        # Read Excel file
        df = pd.read_excel(uploaded_file)

        # Standardize column names
        column_mapping = {
            'date': 'Date', 'Date': 'Date', 'DATE': 'Date',
            'stock_symbol': 'Stock_Symbol', 'Stock_Symbol': 'Stock_Symbol', 'STOCK_SYMBOL': 'Stock_Symbol',
            'symbol': 'Stock_Symbol', 'Symbol': 'Stock_Symbol', 'SYMBOL': 'Stock_Symbol',
            'transaction_type': 'Transaction_Type', 'Transaction_Type': 'Transaction_Type', 'TRANSACTION_TYPE': 'Transaction_Type',
            'type': 'Transaction_Type', 'Type': 'Transaction_Type', 'TYPE': 'Transaction_Type',
            'quantity': 'Quantity', 'Quantity': 'Quantity', 'QUANTITY': 'Quantity',
            'qty': 'Quantity', 'Qty': 'Quantity', 'QTY': 'Quantity',
            'price': 'Price', 'Price': 'Price', 'PRICE': 'Price',
            'rate': 'Price', 'Rate': 'Price', 'RATE': 'Price',
            'brokerage': 'Brokerage', 'Brokerage': 'Brokerage', 'BROKERAGE': 'Brokerage',
            'charges': 'Brokerage', 'Charges': 'Brokerage', 'CHARGES': 'Brokerage'
        }

        # Rename columns
        df = df.rename(columns=column_mapping)

        # Ensure required columns exist
        required_columns = ['Date', 'Stock_Symbol', 'Transaction_Type', 'Quantity', 'Price']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Required column '{col}' not found in Excel file")

        # Add Brokerage column if not present
        if 'Brokerage' not in df.columns:
            df['Brokerage'] = 0.0

        # Data type conversions
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')
        df['Price'] = pd.to_numeric(df['Price'], errors='coerce')
        df['Brokerage'] = pd.to_numeric(df['Brokerage'], errors='coerce').fillna(0)

        # Clean string columns
        df['Stock_Symbol'] = df['Stock_Symbol'].astype(str).str.upper().str.strip()
        df['Transaction_Type'] = df['Transaction_Type'].astype(str).str.title().str.strip()

        # Remove rows with invalid data
        df = df.dropna(subset=['Date', 'Stock_Symbol', 'Transaction_Type', 'Quantity', 'Price'])

        return df

    except Exception as e:
        raise Exception(f"Error processing Excel file: {str(e)}")

def validate_excel_data(df):
    """Validate the processed Excel data"""
    try:
        # Check if DataFrame is empty
        if df.empty:
            return False

        # Check for required columns
        required_columns = ['Date', 'Stock_Symbol', 'Transaction_Type', 'Quantity', 'Price']
        for col in required_columns:
            if col not in df.columns:
                return False

        # Validate data types and values
        validation_errors = []

        # Date validation
        if df['Date'].isnull().any():
            validation_errors.append("Invalid dates found")

        # Stock symbol validation
        if df['Stock_Symbol'].isnull().any() or df['Stock_Symbol'].str.len().eq(0).any():
            validation_errors.append("Empty stock symbols found")

        # Transaction type validation
        valid_transaction_types = ['Buy', 'Sell', 'BUY', 'SELL', 'buy', 'sell']
        if not df['Transaction_Type'].isin(valid_transaction_types).all():
            validation_errors.append("Invalid transaction types found. Must be 'Buy' or 'Sell'")

        # Quantity validation
        if df['Quantity'].isnull().any() or (df['Quantity'] <= 0).any():
            validation_errors.append("Invalid quantities found. Must be positive numbers")

        # Price validation
        if df['Price'].isnull().any() or (df['Price'] <= 0).any():
            validation_errors.append("Invalid prices found. Must be positive numbers")

        # Brokerage validation
        if 'Brokerage' in df.columns and (df['Brokerage'] < 0).any():
            validation_errors.append("Invalid brokerage charges found. Must be non-negative")

        # Print validation errors for debugging
        if validation_errors:
            print("Validation errors:", validation_errors)
            return False

        return True

    except Exception as e:
        print(f"Error validating Excel data: {str(e)}")
        return False
