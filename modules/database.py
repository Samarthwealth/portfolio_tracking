import sqlite3
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np
from typing import Dict, List, Optional, Tuple

class DatabaseManager:
    def __init__(self, db_name="portfolio_tracker_pro.db"):
        self.db_name = db_name
        self.init_database()

    def init_database(self):
        """Initialize database with all required tables"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Clients table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            initial_cash REAL NOT NULL DEFAULT 0,
            risk_profile TEXT DEFAULT 'Moderate',
            created_date TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Enhanced transactions table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            stock_symbol TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            date TEXT NOT NULL,
            brokerage REAL DEFAULT 0,
            realized_profit REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_name) REFERENCES clients (name)
        )
        """)

        # Cash transactions table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cash_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_name) REFERENCES clients (name)
        )
        """)

        # Stock info cache table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_info (
            symbol TEXT PRIMARY KEY,
            sector TEXT,
            industry TEXT,
            market_cap REAL,
            last_updated TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        conn.commit()
        conn.close()

    def add_client(self, name: str, initial_cash: float, risk_profile: str = "Moderate") -> bool:
        """Add a new client"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            cursor.execute("""
            INSERT INTO clients (name, initial_cash, risk_profile)
            VALUES (?, ?, ?)
            """, (name, initial_cash, risk_profile))

            # Add initial cash as a deposit
            cursor.execute("""
            INSERT INTO cash_transactions (client_name, transaction_type, amount, date, description)
            VALUES (?, 'Deposit', ?, ?, 'Initial investment')
            """, (name, initial_cash, datetime.now().strftime('%Y-%m-%d')))

            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            print(f"Error adding client: {e}")
            return False

    def delete_client(self, client_name: str) -> bool:
        """Delete a client and all associated data"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            # Delete all transactions
            cursor.execute("DELETE FROM transactions WHERE client_name = ?", (client_name,))

            # Delete all cash transactions
            cursor.execute("DELETE FROM cash_transactions WHERE client_name = ?", (client_name,))

            # Delete the client
            cursor.execute("DELETE FROM clients WHERE name = ?", (client_name,))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"Error deleting client: {e}")
            return False

    def get_all_clients(self) -> List[Tuple]:
        """Get all clients"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM clients ORDER BY name")
        clients = cursor.fetchall()

        conn.close()
        return clients

    def get_client_data(self, client_name: str) -> Optional[Tuple]:
        """Get specific client data"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM clients WHERE name = ?", (client_name,))
        client = cursor.fetchone()

        conn.close()
        return client

    def add_transaction(self, client_name: str, stock_symbol: str, transaction_type: str, 
                       quantity: int, price: float, date: str, brokerage: float = 0) -> bool:
        """Add a stock transaction with realized profit calculation"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            realized_profit = 0

            # Calculate realized profit for sell transactions
            if transaction_type.upper() == 'SELL':
                realized_profit = self._calculate_realized_profit(
                    client_name, stock_symbol, quantity, price, brokerage
                )

                # Update cash balance
                cash_amount = (quantity * price) - brokerage
                cursor.execute("""
                INSERT INTO cash_transactions (client_name, transaction_type, amount, date, description)
                VALUES (?, 'Deposit', ?, ?, ?)
                """, (client_name, cash_amount, date, f'Sale of {quantity} shares of {stock_symbol}'))

            else:  # BUY transaction
                # Deduct cash
                cash_amount = (quantity * price) + brokerage
                cursor.execute("""
                INSERT INTO cash_transactions (client_name, transaction_type, amount, date, description)
                VALUES (?, 'Withdrawal', ?, ?, ?)
                """, (client_name, cash_amount, date, f'Purchase of {quantity} shares of {stock_symbol}'))

            # Add the transaction
            cursor.execute("""
            INSERT INTO transactions (client_name, stock_symbol, transaction_type, quantity, 
                                    price, date, brokerage, realized_profit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (client_name, stock_symbol, transaction_type, quantity, price, date, brokerage, realized_profit))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"Error adding transaction: {e}")
            return False

    def _calculate_realized_profit(self, client_name: str, stock_symbol: str, 
                                 sell_quantity: int, sell_price: float, brokerage: float) -> float:
        """Calculate realized profit using FIFO method"""
        try:
            conn = sqlite3.connect(self.db_name)

            # Get all buy transactions for this stock, ordered by date
            df = pd.read_sql_query("""
            SELECT * FROM transactions 
            WHERE client_name = ? AND stock_symbol = ? AND transaction_type = 'Buy'
            ORDER BY date ASC
            """, conn, params=(client_name, stock_symbol))

            conn.close()

            if df.empty:
                return 0

            remaining_sell = sell_quantity
            total_cost_basis = 0

            for _, row in df.iterrows():
                if remaining_sell <= 0:
                    break

                available_qty = row['quantity']
                qty_to_sell = min(remaining_sell, available_qty)

                cost_basis = qty_to_sell * row['price']
                total_cost_basis += cost_basis

                remaining_sell -= qty_to_sell

            sell_value = sell_quantity * sell_price
            realized_profit = sell_value - total_cost_basis - brokerage

            return realized_profit

        except Exception as e:
            print(f"Error calculating realized profit: {e}")
            return 0

    def add_cash_transaction(self, client_name: str, transaction_type: str, 
                           amount: float, date: str, description: str = "") -> bool:
        """Add cash transaction (deposit/withdrawal)"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            cursor.execute("""
            INSERT INTO cash_transactions (client_name, transaction_type, amount, date, description)
            VALUES (?, ?, ?, ?, ?)
            """, (client_name, transaction_type, amount, date, description))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"Error adding cash transaction: {e}")
            return False

    def get_cash_balance(self, client_name: str) -> float:
        """Get current cash balance for client"""
        try:
            conn = sqlite3.connect(self.db_name)

            df = pd.read_sql_query("""
            SELECT transaction_type, SUM(amount) as total_amount
            FROM cash_transactions
            WHERE client_name = ?
            GROUP BY transaction_type
            """, conn, params=(client_name,))

            conn.close()

            deposits = df[df['transaction_type'] == 'Deposit']['total_amount'].sum() if not df.empty else 0
            withdrawals = df[df['transaction_type'] == 'Withdrawal']['total_amount'].sum() if not df.empty else 0

            return deposits - withdrawals

        except Exception as e:
            print(f"Error getting cash balance: {e}")
            return 0

    def get_cash_transactions(self, client_name: str) -> pd.DataFrame:
        """Get all cash transactions for a client"""
        try:
            conn = sqlite3.connect(self.db_name)

            df = pd.read_sql_query("""
            SELECT * FROM cash_transactions
            WHERE client_name = ?
            ORDER BY date DESC, created_at DESC
            """, conn, params=(client_name,))

            conn.close()
            return df

        except Exception as e:
            print(f"Error getting cash transactions: {e}")
            return pd.DataFrame()

    def get_cash_stats(self, client_name: str) -> Dict:
        """Get cash transaction statistics"""
        try:
            conn = sqlite3.connect(self.db_name)

            df = pd.read_sql_query("""
            SELECT transaction_type, SUM(amount) as total_amount
            FROM cash_transactions
            WHERE client_name = ?
            GROUP BY transaction_type
            """, conn, params=(client_name,))

            conn.close()

            stats = {'total_deposits': 0, 'total_withdrawals': 0}
            for _, row in df.iterrows():
                if row['transaction_type'] == 'Deposit':
                    stats['total_deposits'] = row['total_amount']
                else:
                    stats['total_withdrawals'] = row['total_amount']

            stats['net_cash_flow'] = stats.get('total_deposits', 0) - stats.get('total_withdrawals', 0)

            return stats

        except Exception as e:
            print(f"Error getting cash stats: {e}")
            return {'total_deposits': 0, 'total_withdrawals': 0, 'net_cash_flow': 0}

    def get_current_holdings(self, client_name: str) -> pd.DataFrame:
        """Get current stock holdings"""
        try:
            conn = sqlite3.connect(self.db_name)

            df = pd.read_sql_query("""
            SELECT stock_symbol, 
                   SUM(CASE WHEN transaction_type = 'Buy' THEN quantity ELSE -quantity END) as quantity,
                   SUM(CASE WHEN transaction_type = 'Buy' THEN quantity * price + brokerage 
                            ELSE -quantity * price + brokerage END) as total_cost
            FROM transactions
            WHERE client_name = ?
            GROUP BY stock_symbol
            HAVING quantity > 0
            """, conn, params=(client_name,))

            conn.close()

            if df.empty:
                return df

            # Add current prices and calculations
            df['avg_price'] = df['total_cost'] / df['quantity']
            df['current_price'] = df['stock_symbol'].apply(self._get_current_price)
            df['current_value'] = df['quantity'] * df['current_price']
            df['unrealized_pnl'] = df['current_value'] - df['total_cost']
            df['unrealized_pnl_pct'] = (df['unrealized_pnl'] / df['total_cost'] * 100).round(2)

            return df.round(2)

        except Exception as e:
            print(f"Error getting holdings: {e}")
            return pd.DataFrame()

    def get_current_holdings_with_realized(self, client_name: str) -> pd.DataFrame:
        """Get current holdings with realized profit information"""
        try:
            holdings_df = self.get_current_holdings(client_name)

            if holdings_df.empty:
                return holdings_df

            # Add realized profits for each stock
            conn = sqlite3.connect(self.db_name)

            for idx, row in holdings_df.iterrows():
                stock_symbol = row['stock_symbol']

                # Get total realized profit for this stock
                cursor = conn.cursor()
                cursor.execute("""
                SELECT COALESCE(SUM(realized_profit), 0) as total_realized
                FROM transactions
                WHERE client_name = ? AND stock_symbol = ? AND transaction_type = 'Sell'
                """, (client_name, stock_symbol))

                result = cursor.fetchone()
                realized_profit = result[0] if result else 0

                holdings_df.at[idx, 'realized_pnl'] = realized_profit
                holdings_df.at[idx, 'total_pnl'] = realized_profit + row['unrealized_pnl']

            conn.close()
            return holdings_df.round(2)

        except Exception as e:
            print(f"Error getting holdings with realized: {e}")
            return pd.DataFrame()

    def get_total_realized_profit(self, client_name: str) -> float:
        """Get total realized profit for all transactions"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            cursor.execute("""
            SELECT COALESCE(SUM(realized_profit), 0) as total_realized
            FROM transactions
            WHERE client_name = ? AND transaction_type = 'Sell'
            """, (client_name,))

            result = cursor.fetchone()
            conn.close()

            return result[0] if result else 0

        except Exception as e:
            print(f"Error getting total realized profit: {e}")
            return 0

    def get_all_transactions_with_realized(self, client_name: str) -> pd.DataFrame:
        """Get all transactions with realized profit information"""
        try:
            conn = sqlite3.connect(self.db_name)

            df = pd.read_sql_query("""
            SELECT *, (quantity * price + brokerage) as total_amount
            FROM transactions
            WHERE client_name = ?
            ORDER BY date DESC, created_at DESC
            """, conn, params=(client_name,))

            conn.close()
            return df

        except Exception as e:
            print(f"Error getting transactions: {e}")
            return pd.DataFrame()

    def _get_current_price(self, symbol: str) -> float:
        """Get current price for a stock symbol"""
        try:
            # Add .NS for NSE stocks if not present
            if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
                symbol += '.NS'

            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='1d')

            if not hist.empty:
                return float(hist['Close'].iloc[-1])
            else:
                # Fallback to info if history fails
                info = ticker.info
                return float(info.get('currentPrice', info.get('regularMarketPrice', 100)))

        except Exception as e:
            print(f"Error getting price for {symbol}: {e}")
            return 100.0  # Default price

    def get_portfolio_summary(self, client_name: str) -> Dict:
        """Get portfolio summary statistics"""
        holdings_df = self.get_current_holdings_with_realized(client_name)

        if holdings_df.empty:
            return {
                'invested_amount': 0,
                'current_value': 0,
                'total_pnl': 0,
                'unrealized_pnl': 0,
                'realized_pnl': 0
            }

        return {
            'invested_amount': holdings_df['total_cost'].sum(),
            'current_value': holdings_df['current_value'].sum(),
            'total_pnl': holdings_df['unrealized_pnl'].sum(),
            'unrealized_pnl': holdings_df['unrealized_pnl'].sum(),
            'realized_pnl': holdings_df['realized_pnl'].sum() if 'realized_pnl' in holdings_df.columns else 0
        }

    def get_transaction_stats(self, client_name: str) -> Dict:
        """Get transaction statistics"""
        try:
            conn = sqlite3.connect(self.db_name)

            df = pd.read_sql_query("""
            SELECT transaction_type, COUNT(*) as count, COUNT(DISTINCT stock_symbol) as unique_stocks
            FROM transactions
            WHERE client_name = ?
            GROUP BY transaction_type
            """, conn, params=(client_name,))

            conn.close()

            stats = {'buy_orders': 0, 'sell_orders': 0}
            total_transactions = 0
            unique_stocks = set()

            for _, row in df.iterrows():
                if row['transaction_type'] == 'Buy':
                    stats['buy_orders'] = row['count']
                else:
                    stats['sell_orders'] = row['count']
                total_transactions += row['count']
                unique_stocks.add(row['unique_stocks'])

            stats['total_transactions'] = total_transactions
            stats['unique_stocks'] = len(unique_stocks)

            return stats

        except Exception as e:
            print(f"Error getting transaction stats: {e}")
            return {'buy_orders': 0, 'sell_orders': 0, 'total_transactions': 0, 'unique_stocks': 0}

    def get_transaction_count(self, client_name: str) -> int:
        """Get total transaction count"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM transactions WHERE client_name = ?", (client_name,))
            count = cursor.fetchone()[0]

            conn.close()
            return count

        except Exception as e:
            print(f"Error getting transaction count: {e}")
            return 0

    def get_all_transactions(self, client_name: str) -> pd.DataFrame:
        """Get all transactions for a client"""
        try:
            conn = sqlite3.connect(self.db_name)

            df = pd.read_sql_query("""
            SELECT * FROM transactions
            WHERE client_name = ?
            ORDER BY date DESC, created_at DESC
            """, conn, params=(client_name,))

            conn.close()
            return df

        except Exception as e:
            print(f"Error getting all transactions: {e}")
            return pd.DataFrame()
