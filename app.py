import streamlit as st
import pandas as pd
import yfinance as yf
import sqlite3
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import seaborn as sns
import numpy as np
from datetime import datetime, timedelta
import os
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

# Import custom modules
from modules.pdf_generator import generate_advanced_pdf
from modules.excel_generator import generate_excel_report
from modules.excel_processor import process_excel_upload, validate_excel_data
from modules.database import DatabaseManager
from modules.visualizations import create_performance_charts, create_allocation_charts
from modules.utils import format_currency, calculate_returns

# Page configuration
st.set_page_config(
    page_title="Advanced Portfolio Tracker Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .profit-positive {
        color: #00C851;
        font-weight: bold;
    }
    .profit-negative {
        color: #ff4444;
        font-weight: bold;
    }
    .cash-balance {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    .realized-profit {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    .stButton > button {
        border-radius: 10px;
        height: 3em;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database
@st.cache_resource
def init_db():
    return DatabaseManager()

db = init_db()

# Sidebar
st.sidebar.title("🎯 Portfolio Control Panel Pro")

# Client Management Section
st.sidebar.header("👥 Client Management")

# Add New Client
with st.sidebar.expander("➕ Add New Client", expanded=False):
    client_name = st.text_input("Client Name")
    initial_cash = st.number_input("Initial Cash (₹)", min_value=0.0, value=100000.0, step=10000.0)
    risk_profile = st.selectbox("Risk Profile", ["Conservative", "Moderate", "Aggressive"])

    if st.button("Add Client", key="add_client"):
        if client_name:
            success = db.add_client(client_name, initial_cash, risk_profile)
            if success:
                st.success(f"✅ Client '{client_name}' added successfully!")
                st.rerun()
            else:
                st.error("❌ Client already exists or error occurred.")
        else:
            st.error("⚠️ Please enter a client name.")

# Select and Delete Client
clients = db.get_all_clients()
client_list = [client[1] for client in clients]
selected_client = st.sidebar.selectbox("Select Client", [""] + client_list, key="client_selector")

if selected_client:
    st.sidebar.success(f"✅ Selected: {selected_client}")

    # Delete Client Option
    with st.sidebar.expander("🗑️ Delete Client", expanded=False):
        st.warning(f"⚠️ Delete client '{selected_client}'?")
        st.write("This will permanently delete:")
        st.write("• All transactions")
        st.write("• All cash movements")
        st.write("• All portfolio data")

        confirm_delete = st.text_input("Type 'DELETE' to confirm:", key="delete_confirm")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Delete", key="delete_client"):
                if confirm_delete == "DELETE":
                    success = db.delete_client(selected_client)
                    if success:
                        st.success(f"✅ Client deleted!")
                        st.rerun()
                    else:
                        st.error("❌ Error deleting client.")
                else:
                    st.error("❌ Type 'DELETE' to confirm.")

        with col2:
            if st.button("❌ Cancel", key="cancel_delete"):
                st.info("Cancelled.")

# Main Application
st.title("📊 Advanced Portfolio Management System Pro")
st.markdown("### Professional Portfolio Tracking, Cash Management & Reporting Platform")

if not selected_client:
    st.info("🚀 Please select a client from the sidebar to access the portfolio management features.")
    st.markdown("""
    ## 🏆 Welcome to Advanced Portfolio Tracker Pro v2.0!

    ### ✨ Key Features:
    - **💰 Realized Profit Tracking**: FIFO-based calculations for accurate profit tracking
    - **🏦 Complete Cash Management**: Track deposits, withdrawals, and cash flows
    - **📊 Professional Reports**: Generate PDF and Excel reports with charts
    - **📈 Real-time Analytics**: Interactive dashboards with live stock prices
    - **👥 Multi-Client Support**: Manage multiple portfolios seamlessly
    - **📥 Bulk Import**: Excel file import with validation

    ### 🚀 Getting Started:
    1. **Add a Client** using the sidebar
    2. **Add transactions** manually or via Excel upload
    3. **Manage cash** with deposits and withdrawals
    4. **View analytics** and generate professional reports
    """)
    st.stop()

# Create tabs for different functionalities
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📈 Dashboard", "💰 Cash Management", "📥 Upload Data", 
    "🎯 Transactions", "📊 Analytics", "📄 Reports", "📋 Ledger"
])

with tab1:
    st.header(f"📈 Portfolio Dashboard - {selected_client}")

    # Get client data
    client_data = db.get_client_data(selected_client)
    if client_data:
        initial_cash = client_data[2]
        risk_profile = client_data[3] if len(client_data) > 3 else "Not Set"
    else:
        initial_cash = 0
        risk_profile = "Not Set"

    # Portfolio summary metrics
    portfolio_summary = db.get_portfolio_summary(selected_client)
    cash_balance = db.get_cash_balance(selected_client)
    realized_profits = db.get_total_realized_profit(selected_client)

    # Top row - Key metrics
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h4>💰 Cash Balance</h4>
            <h2>{format_currency(cash_balance)}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        invested_amount = portfolio_summary.get('invested_amount', 0)
        st.markdown(f"""
        <div class="metric-card">
            <h4>📈 Invested</h4>
            <h2>{format_currency(invested_amount)}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        current_value = portfolio_summary.get('current_value', 0)
        st.markdown(f"""
        <div class="metric-card">
            <h4>💎 Current Value</h4>
            <h2>{format_currency(current_value)}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        unrealized_pnl = portfolio_summary.get('total_pnl', 0)
        unrealized_pct = (unrealized_pnl / invested_amount * 100) if invested_amount > 0 else 0
        color_class = "profit-positive" if unrealized_pnl >= 0 else "profit-negative"
        st.markdown(f"""
        <div class="metric-card">
            <h4>📊 Unrealized P&L</h4>
            <h2 class="{color_class}">{format_currency(unrealized_pnl)}</h2>
            <p>({unrealized_pct:+.2f}%)</p>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        realized_pct = (realized_profits / invested_amount * 100) if invested_amount > 0 else 0
        color_class = "profit-positive" if realized_profits >= 0 else "profit-negative"
        st.markdown(f"""
        <div class="realized-profit">
            <h4>✅ Realized P&L</h4>
            <h2 class="{color_class}">{format_currency(realized_profits)}</h2>
            <p>({realized_pct:+.2f}%)</p>
        </div>
        """, unsafe_allow_html=True)

    # Total portfolio value
    total_portfolio_value = cash_balance + current_value
    total_returns = realized_profits + unrealized_pnl
    total_returns_pct = (total_returns / initial_cash * 100) if initial_cash > 0 else 0

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 2rem; border-radius: 15px; color: white; text-align: center; margin: 1rem 0;">
        <h2>🏆 Total Portfolio Value: {format_currency(total_portfolio_value)}</h2>
        <h3>Total Returns: {format_currency(total_returns)} ({total_returns_pct:+.2f}%)</h3>
    </div>
    """, unsafe_allow_html=True)

    # Current Holdings with Realized Profits
    holdings_df = db.get_current_holdings_with_realized(selected_client)
    if not holdings_df.empty:
        st.subheader("📋 Current Holdings with Profit Analysis")

        # Format the dataframe for display
        display_df = holdings_df.copy()
        for col in ['avg_price', 'current_price', 'unrealized_pnl', 'realized_pnl', 'current_value', 'total_pnl']:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(lambda x: f"₹{x:,.2f}")

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )

        # Portfolio allocation chart
        fig_allocation = create_allocation_charts(holdings_df)
        if fig_allocation:
            st.plotly_chart(fig_allocation, use_container_width=True)
    else:
        st.info("No current holdings found. Add some transactions to see the portfolio.")

with tab2:
    st.header("💰 Cash Management")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("💳 Add Cash Transaction")
        with st.form("cash_transaction"):
            tcol1, tcol2 = st.columns(2)

            with tcol1:
                transaction_type = st.selectbox("Transaction Type", ["Deposit", "Withdrawal"])
                amount = st.number_input("Amount (₹)", min_value=0.01, value=1000.0, step=100.0)

            with tcol2:
                transaction_date = st.date_input("Date", value=datetime.now().date())
                description = st.text_input("Description", placeholder="e.g., Initial deposit, Dividend received")

            submitted = st.form_submit_button("💰 Add Cash Transaction", type="primary")

            if submitted:
                if amount > 0:
                    success = db.add_cash_transaction(
                        selected_client,
                        transaction_type,
                        amount,
                        transaction_date.strftime('%Y-%m-%d'),
                        description
                    )

                    if success:
                        st.success("✅ Cash transaction added successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Error adding cash transaction.")
                else:
                    st.error("⚠️ Amount must be greater than 0.")

    with col2:
        st.subheader("💰 Cash Summary")
        cash_balance = db.get_cash_balance(selected_client)
        cash_stats = db.get_cash_stats(selected_client)

        st.markdown(f"""
        <div class="cash-balance">
            <h3>Available Cash</h3>
            <h2>{format_currency(cash_balance)}</h2>
        </div>
        """, unsafe_allow_html=True)

        if cash_stats:
            st.metric("Total Deposits", format_currency(cash_stats.get('total_deposits', 0)))
            st.metric("Total Withdrawals", format_currency(cash_stats.get('total_withdrawals', 0)))
            st.metric("Net Cash Flow", format_currency(cash_stats.get('net_cash_flow', 0)))

    # Cash Transaction History
    st.subheader("📋 Cash Transaction History")
    cash_transactions_df = db.get_cash_transactions(selected_client)

    if not cash_transactions_df.empty:
        # Format for display
        display_cash_df = cash_transactions_df.copy()
        display_cash_df['amount'] = display_cash_df['amount'].apply(lambda x: f"₹{x:,.2f}")

        st.dataframe(display_cash_df, use_container_width=True, hide_index=True)
    else:
        st.info("No cash transactions found.")

with tab3:
    st.header("📥 Upload Transaction Data")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Upload Excel File")
        uploaded_file = st.file_uploader(
            "Choose Excel file",
            type=['xlsx', 'xls'],
            help="Upload Excel file with transaction data"
        )

    with col2:
        st.subheader("Download Template")
        # Enhanced sample Excel template
        sample_data = {
            'Date': ['2024-01-15', '2024-01-20', '2024-02-10', '2024-02-15'],
            'Stock_Symbol': ['RELIANCE', 'TCS', 'INFY', 'RELIANCE'],
            'Transaction_Type': ['Buy', 'Buy', 'Buy', 'Sell'],
            'Quantity': [10, 5, 8, 5],
            'Price': [2500.50, 3400.25, 1650.00, 2600.00],
            'Brokerage': [25.00, 17.00, 13.20, 13.00]
        }
        sample_df = pd.DataFrame(sample_data)

        # Convert to Excel bytes
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            sample_df.to_excel(writer, sheet_name='Transactions', index=False)
        output.seek(0)

        st.download_button(
            label="📥 Download Template",
            data=output,
            file_name="transaction_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    if uploaded_file is not None:
        try:
            transactions_df = process_excel_upload(uploaded_file)

            if validate_excel_data(transactions_df):
                st.success("✅ Excel file validated successfully!")

                st.subheader("📋 Data Preview")
                st.dataframe(transactions_df.head(10), use_container_width=True)

                if st.button("📥 Import Transactions", type="primary"):
                    success_count = 0
                    error_count = 0

                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    for idx, row in transactions_df.iterrows():
                        progress = (idx + 1) / len(transactions_df)
                        progress_bar.progress(progress)
                        status_text.text(f"Processing transaction {idx + 1} of {len(transactions_df)}")

                        success = db.add_transaction(
                            selected_client,
                            row['Stock_Symbol'],
                            row['Transaction_Type'],
                            row['Quantity'],
                            row['Price'],
                            row['Date'].strftime('%Y-%m-%d'),
                            row.get('Brokerage', 0)
                        )
                        if success:
                            success_count += 1
                        else:
                            error_count += 1

                    status_text.text("Import completed!")
                    st.success(f"✅ Successfully imported {success_count} transactions!")
                    if error_count > 0:
                        st.warning(f"⚠️ {error_count} transactions failed to import.")
                    st.rerun()
            else:
                st.error("❌ Excel file validation failed. Please check the format.")

        except Exception as e:
            st.error(f"Error processing file: {str(e)}")

with tab4:
    st.header("🎯 Manual Transaction Entry")

    col1, col2 = st.columns([2, 1])

    with col1:
        with st.form("add_transaction"):
            st.subheader("Add New Transaction")

            tcol1, tcol2 = st.columns(2)

            with tcol1:
                stock_symbol = st.text_input("Stock Symbol (e.g., RELIANCE)", key="stock_input")
                transaction_type = st.selectbox("Transaction Type", ["Buy", "Sell"])
                quantity = st.number_input("Quantity", min_value=1, value=1)

            with tcol2:
                price = st.number_input("Price per Share (₹)", min_value=0.01, value=100.0, step=0.01)
                brokerage = st.number_input("Brokerage (₹)", min_value=0.0, value=0.0, step=0.01)
                transaction_date = st.date_input("Transaction Date", value=datetime.now().date())

            submitted = st.form_submit_button("🎯 Add Transaction", type="primary")

            if submitted and stock_symbol:
                success = db.add_transaction(
                    selected_client,
                    stock_symbol.upper(),
                    transaction_type,
                    quantity,
                    price,
                    transaction_date.strftime('%Y-%m-%d'),
                    brokerage
                )

                if success:
                    st.success("✅ Transaction added successfully!")
                    st.rerun()
                else:
                    st.error("❌ Error adding transaction.")
            elif submitted and not stock_symbol:
                st.error("⚠️ Please enter a stock symbol.")

    with col2:
        st.subheader("📊 Quick Stats")
        stats = db.get_transaction_stats(selected_client)
        if stats:
            st.metric("Total Transactions", stats.get('total_transactions', 0))
            st.metric("Total Buy Orders", stats.get('buy_orders', 0))
            st.metric("Total Sell Orders", stats.get('sell_orders', 0))
            st.metric("Unique Stocks", stats.get('unique_stocks', 0))

    # Transaction History with Realized Profits
    st.subheader("📋 Transaction History")
    transactions_df = db.get_all_transactions_with_realized(selected_client)

    if not transactions_df.empty:
        # Add filters
        col1, col2, col3 = st.columns(3)

        with col1:
            stock_filter = st.selectbox("Filter by Stock", ["All"] + list(transactions_df['stock_symbol'].unique()))

        with col2:
            type_filter = st.selectbox("Filter by Type", ["All", "Buy", "Sell"])

        with col3:
            date_range = st.date_input("Date Range", 
                                     value=(datetime.now().date() - timedelta(days=30), 
                                           datetime.now().date()))

        # Apply filters
        filtered_df = transactions_df.copy()

        if stock_filter != "All":
            filtered_df = filtered_df[filtered_df['stock_symbol'] == stock_filter]

        if type_filter != "All":
            filtered_df = filtered_df[filtered_df['transaction_type'] == type_filter]

        if len(date_range) == 2:
            filtered_df = filtered_df[
                (pd.to_datetime(filtered_df['date']).dt.date >= date_range[0]) &
                (pd.to_datetime(filtered_df['date']).dt.date <= date_range[1])
            ]

        # Format currency columns
        display_trans_df = filtered_df.copy()
        for col in ['price', 'total_amount', 'brokerage', 'realized_profit']:
            if col in display_trans_df.columns:
                display_trans_df[col] = display_trans_df[col].apply(lambda x: f"₹{x:,.2f}" if pd.notna(x) else "₹0.00")

        st.dataframe(display_trans_df, use_container_width=True, hide_index=True)
    else:
        st.info("No transactions found. Add some transactions to see them here.")

with tab5:
    st.header("📊 Advanced Analytics")

    if db.get_transaction_count(selected_client) == 0:
        st.info("No data available for analytics. Please add some transactions first.")
    else:
        # Performance charts
        fig_performance = create_performance_charts(selected_client, db)
        if fig_performance:
            st.plotly_chart(fig_performance, use_container_width=True)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🎯 Portfolio Metrics")
            portfolio_summary = db.get_portfolio_summary(selected_client)
            holdings_df = db.get_current_holdings_with_realized(selected_client)

            if not holdings_df.empty:
                st.metric("Number of Holdings", len(holdings_df))
                st.metric("Best Performer", 
                         holdings_df.loc[holdings_df['unrealized_pnl_pct'].idxmax(), 'stock_symbol'] + 
                         f" (+{holdings_df['unrealized_pnl_pct'].max():.1f}%)")
                st.metric("Worst Performer", 
                         holdings_df.loc[holdings_df['unrealized_pnl_pct'].idxmin(), 'stock_symbol'] + 
                         f" ({holdings_df['unrealized_pnl_pct'].min():.1f}%)")

        with col2:
            st.subheader("🏭 Portfolio Insights")
            if not holdings_df.empty:
                winners = holdings_df[holdings_df['unrealized_pnl'] > 0]
                losers = holdings_df[holdings_df['unrealized_pnl'] < 0]

                st.metric("Profitable Positions", f"{len(winners)} ({len(winners)/len(holdings_df)*100:.1f}%)")
                st.metric("Loss Positions", f"{len(losers)} ({len(losers)/len(holdings_df)*100:.1f}%)")

                # Concentration risk
                total_value = holdings_df['current_value'].sum()
                max_holding_pct = holdings_df['current_value'].max() / total_value * 100
                st.metric("Largest Holding", f"{max_holding_pct:.1f}% of portfolio")

with tab6:
    st.header("📄 Professional Reports")

    col1, col2, col3 = st.columns(3)

    with col1:
        report_type = st.selectbox(
            "Report Type",
            ["Comprehensive Portfolio Report", "Performance Summary", "Holdings Statement", 
             "Tax Statement", "Realized Profits Report", "Cash Flow Statement"]
        )

    with col2:
        report_period = st.selectbox(
            "Report Period",
            ["Last 30 Days", "Last 3 Months", "Last 6 Months", "Last 1 Year", "All Time"]
        )

    with col3:
        include_charts = st.checkbox("Include Charts", value=True)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📄 Generate PDF Report", type="primary", use_container_width=True):
            with st.spinner("Generating professional PDF report..."):
                try:
                    pdf_buffer = generate_advanced_pdf(
                        selected_client,
                        db,
                        report_type,
                        report_period,
                        include_charts
                    )

                    if pdf_buffer:
                        st.success("✅ PDF Report generated successfully!")

                        report_filename = f"{selected_client}_{report_type.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

                        st.download_button(
                            label="📥 Download PDF Report",
                            data=pdf_buffer,
                            file_name=report_filename,
                            mime="application/pdf",
                            use_container_width=True
                        )
                    else:
                        st.error("❌ Error generating PDF report.")

                except Exception as e:
                    st.error(f"Error generating PDF report: {str(e)}")

    with col2:
        if st.button("📊 Generate Excel Report", type="secondary", use_container_width=True):
            with st.spinner("Generating detailed Excel report..."):
                try:
                    excel_buffer = generate_excel_report(
                        selected_client,
                        db,
                        report_type,
                        report_period
                    )

                    if excel_buffer:
                        st.success("✅ Excel Report generated successfully!")

                        report_filename = f"{selected_client}_{report_type.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

                        st.download_button(
                            label="📥 Download Excel Report",
                            data=excel_buffer,
                            file_name=report_filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    else:
                        st.error("❌ Error generating Excel report.")

                except Exception as e:
                    st.error(f"Error generating Excel report: {str(e)}")

    # Report preview
    st.subheader("📋 Report Preview")
    if db.get_transaction_count(selected_client) > 0:
        preview_data = db.get_portfolio_summary(selected_client)
        cash_balance = db.get_cash_balance(selected_client)
        realized_profits = db.get_total_realized_profit(selected_client)

        preview_data['cash_balance'] = cash_balance
        preview_data['realized_profits'] = realized_profits
        preview_data['total_portfolio_value'] = cash_balance + preview_data.get('current_value', 0)

        if preview_data:
            st.json(preview_data)
    else:
        st.info("No data available for report preview.")

with tab7:
    st.header("📋 Complete Portfolio Ledger")

    # Ledger filters
    col1, col2, col3 = st.columns(3)

    with col1:
        ledger_type = st.selectbox("Ledger Type", ["All Transactions", "Stock Transactions Only", "Cash Transactions Only"])

    with col2:
        date_from = st.date_input("From Date", value=datetime.now().date() - timedelta(days=365))

    with col3:
        date_to = st.date_input("To Date", value=datetime.now().date())

    # Get ledger data
    if ledger_type == "All Transactions":
        # Combine stock and cash transactions
        stock_trans = db.get_all_transactions_with_realized(selected_client)
        cash_trans = db.get_cash_transactions(selected_client)

        # Create unified ledger
        ledger_data = []

        # Add stock transactions
        for _, row in stock_trans.iterrows():
            ledger_data.append({
                'Date': row['date'],
                'Type': 'Stock Transaction',
                'Description': f"{row['transaction_type']} {row['quantity']} shares of {row['stock_symbol']} @ ₹{row['price']:.2f}",
                'Amount': row['total_amount'] if row['transaction_type'] == 'Buy' else -row['total_amount'],
                'Cash_Impact': f"-₹{row['total_amount']:,.2f}" if row['transaction_type'] == 'Buy' else f"+₹{row['total_amount']:,.2f}",
                'Realized_PL': f"₹{row.get('realized_profit', 0):,.2f}" if row['transaction_type'] == 'Sell' else "N/A"
            })

        # Add cash transactions
        for _, row in cash_trans.iterrows():
            ledger_data.append({
                'Date': row['date'],
                'Type': 'Cash Transaction',
                'Description': f"{row['transaction_type']}: {row.get('description', '')}",
                'Amount': row['amount'] if row['transaction_type'] == 'Deposit' else -row['amount'],
                'Cash_Impact': f"+₹{row['amount']:,.2f}" if row['transaction_type'] == 'Deposit' else f"-₹{row['amount']:,.2f}",
                'Realized_PL': "N/A"
            })

        if ledger_data:
            ledger_df = pd.DataFrame(ledger_data)
            ledger_df['Date'] = pd.to_datetime(ledger_df['Date'])
            ledger_df = ledger_df.sort_values('Date', ascending=False)

            # Apply date filter
            mask = (ledger_df['Date'].dt.date >= date_from) & (ledger_df['Date'].dt.date <= date_to)
            filtered_ledger = ledger_df[mask]

            if not filtered_ledger.empty:
                st.subheader(f"📊 Complete Ledger ({len(filtered_ledger)} entries)")

                # Running balance calculation
                running_balance = 0
                balance_history = []

                for idx, row in filtered_ledger.iterrows():
                    running_balance += row['Amount']
                    balance_history.append(running_balance)

                filtered_ledger['Running_Balance'] = [f"₹{balance:,.2f}" for balance in balance_history]

                # Display ledger
                st.dataframe(
                    filtered_ledger[['Date', 'Type', 'Description', 'Cash_Impact', 'Realized_PL', 'Running_Balance']],
                    use_container_width=True,
                    hide_index=True
                )

                # Summary statistics
                st.subheader("📈 Ledger Summary")
                col1, col2, col3 = st.columns(3)

                with col1:
                    total_inflow = filtered_ledger[filtered_ledger['Amount'] > 0]['Amount'].sum()
                    st.metric("Total Inflow", format_currency(total_inflow))

                with col2:
                    total_outflow = abs(filtered_ledger[filtered_ledger['Amount'] < 0]['Amount'].sum())
                    st.metric("Total Outflow", format_currency(total_outflow))

                with col3:
                    net_flow = total_inflow - total_outflow
                    st.metric("Net Cash Flow", format_currency(net_flow))
            else:
                st.info("No transactions found in the selected date range.")
        else:
            st.info("No transactions found for this client.")

    elif ledger_type == "Stock Transactions Only":
        transactions_df = db.get_all_transactions_with_realized(selected_client)
        if not transactions_df.empty:
            # Apply date filter
            transactions_df['date'] = pd.to_datetime(transactions_df['date'])
            mask = (transactions_df['date'].dt.date >= date_from) & (transactions_df['date'].dt.date <= date_to)
            filtered_trans = transactions_df[mask]

            if not filtered_trans.empty:
                st.subheader(f"📊 Stock Transaction Ledger ({len(filtered_trans)} transactions)")

                # Format for display
                display_df = filtered_trans.copy()
                for col in ['price', 'total_amount', 'brokerage', 'realized_profit']:
                    if col in display_df.columns:
                        display_df[col] = display_df[col].apply(lambda x: f"₹{x:,.2f}" if pd.notna(x) else "₹0.00")

                st.dataframe(display_df, use_container_width=True, hide_index=True)
            else:
                st.info("No stock transactions found in the selected date range.")
        else:
            st.info("No stock transactions found for this client.")

    else:  # Cash Transactions Only
        cash_df = db.get_cash_transactions(selected_client)
        if not cash_df.empty:
            # Apply date filter
            cash_df['date'] = pd.to_datetime(cash_df['date'])
            mask = (cash_df['date'].dt.date >= date_from) & (cash_df['date'].dt.date <= date_to)
            filtered_cash = cash_df[mask]

            if not filtered_cash.empty:
                st.subheader(f"📊 Cash Transaction Ledger ({len(filtered_cash)} transactions)")

                # Calculate running balance
                running_balance = 0
                balance_history = []

                for _, row in filtered_cash.iterrows():
                    if row['transaction_type'] == 'Deposit':
                        running_balance += row['amount']
                    else:
                        running_balance -= row['amount']
                    balance_history.append(f"₹{running_balance:,.2f}")

                filtered_cash['running_balance'] = balance_history
                filtered_cash['amount'] = filtered_cash['amount'].apply(lambda x: f"₹{x:,.2f}")

                st.dataframe(filtered_cash, use_container_width=True, hide_index=True)
            else:
                st.info("No cash transactions found in the selected date range.")
        else:
            st.info("No cash transactions found for this client.")

# Footer
st.markdown("---")
st.markdown(
    f"""
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p>🏢 Advanced Portfolio Management System Pro v2.0 | Built with ❤️ using Streamlit</p>
        <p>📧 Contact: support@portfoliopro.com | 📞 Phone: +91-XXXXX-XXXXX</p>
        <p>💡 Features: Realized P&L Tracking | Cash Management | Professional Reports | Advanced Analytics | Complete Ledger</p>
        <p><small>Last Updated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</small></p>
    </div>
    """,
    unsafe_allow_html=True
)
