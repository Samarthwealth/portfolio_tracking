import streamlit as st
import pandas as pd
import yfinance as yf
import sqlite3
import matplotlib.pyplot as plt
import os
from fpdf import FPDF

# Connect to SQLite DB
conn = sqlite3.connect('portfolio.db', check_same_thread=False)
c = conn.cursor()

# Ensure tables exist
c.execute('''CREATE TABLE IF NOT EXISTS clients (
    client_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT UNIQUE,
    initial_cash REAL DEFAULT 0
)''')

c.execute('''CREATE TABLE IF NOT EXISTS transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT,
    stock_name TEXT,
    transaction_type TEXT,
    quantity INTEGER,
    price REAL,
    date TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS alerts (
    alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT,
    stock_name TEXT,
    target_price REAL,
    stop_loss_price REAL)''')

try:
    c.execute("ALTER TABLE clients ADD COLUMN initial_cash REAL DEFAULT 0")
    conn.commit()
except sqlite3.OperationalError:
    pass

conn.commit()

@st.cache_data(ttl=600)
def get_current_price(symbol):
    try:
        ticker = yf.Ticker(symbol + ".NS")
        data = ticker.history(period="1d")
        return round(data['Close'].iloc[-1], 2) if not data.empty else None
    except:
        return None

def calculate_realized_profit(client):
    df = pd.read_sql("SELECT * FROM transactions WHERE client_name = ?", conn, params=(client,))
    if df.empty:
        return 0, pd.DataFrame()
    profit = 0
    rows = []
    for stock in df['stock_name'].unique():
        buys = df[(df['stock_name'] == stock) & (df['transaction_type'] == 'Buy')]
        sells = df[(df['stock_name'] == stock) & (df['transaction_type'] == 'Sell')]
        if not sells.empty and not buys.empty:
            avg = (buys['quantity'] * buys['price']).sum() / buys['quantity'].sum()
            p = ((sells['price'] - avg) * sells['quantity']).sum()
            profit += p
            rows.append({"Stock Name": stock, "Realized Profit": round(p, 2)})
    return round(profit, 2), pd.DataFrame(rows)

def calculate_unrealized_profit(client):
    df = pd.read_sql("SELECT * FROM transactions WHERE client_name = ?", conn, params=(client,))
    if df.empty:
        return pd.DataFrame(), 0, 0
    rows = []
    unrealized = 0
    invested = 0
    for stock in df['stock_name'].unique():
        buys = df[(df['stock_name'] == stock) & (df['transaction_type'] == 'Buy')]
        sells = df[(df['stock_name'] == stock) & (df['transaction_type'] == 'Sell')]
        qty = buys['quantity'].sum() - sells['quantity'].sum()
        if qty > 0:
            avg = (buys['quantity'] * buys['price']).sum() / buys['quantity'].sum()
            current = get_current_price(stock)
            if current:
                value = current * qty
                pl = (current - avg) * qty
                unrealized += pl
                invested += avg * qty
                rows.append({
                    "Stock Name": stock,
                    "Average Buy Price": round(avg, 2),
                    "Current Market Price": current,
                    "Quantity Held": qty,
                    "Unrealized Profit/Loss": round(pl, 2),
                    "Valuation": round(value, 2)
                })
    return pd.DataFrame(rows), round(unrealized, 2), round(invested, 2)

st.title("📊 Stock Portfolio Tracker")

st.sidebar.header("➕ Add New Client")
client_input = st.sidebar.text_input("Client Name")
initial_cash = st.sidebar.number_input("Initial Cash (₹)", min_value=0.0, value=100000.0)

if st.sidebar.button("Add Client"):
    try:
        c.execute("INSERT INTO clients (client_name, initial_cash) VALUES (?, ?)", (client_input, initial_cash))
        conn.commit()
        st.sidebar.success(f"Client '{client_input}' added!")
    except sqlite3.IntegrityError:
        st.sidebar.error("Client already exists.")

clients = pd.read_sql("SELECT client_name FROM clients", conn)['client_name'].tolist()
selected_client = st.selectbox("Select Client", clients)

if selected_client:
    st.header(f"📥 Add Transaction for {selected_client}")
    stock = st.text_input("Stock Symbol (e.g., RELIANCE)")
    t_type = st.radio("Transaction Type", ["Buy", "Sell"])
    qty = st.number_input("Quantity", 1)
    price = st.number_input("Price", 0.0)
    date = st.date_input("Date")

    if st.button("Add Transaction"):
        c.execute("INSERT INTO transactions (client_name, stock_name, transaction_type, quantity, price, date) VALUES (?, ?, ?, ?, ?, ?)",
                  (selected_client, stock, t_type, qty, price, date))
        conn.commit()
        st.success(f"{t_type} added for {stock}.")

    df_txn = pd.read_sql("SELECT * FROM transactions WHERE client_name = ?", conn, params=(selected_client,))
    if not df_txn.empty:
        st.subheader("📃 Transaction History")
        st.dataframe(df_txn)

        selected_txn_id = st.selectbox("Select Transaction ID to Update/Delete", df_txn['transaction_id'].tolist())
        txn_row = df_txn[df_txn['transaction_id'] == selected_txn_id].iloc[0]

        new_qty = st.number_input("New Quantity", value=txn_row['quantity'], key="upd_qty")
        new_price = st.number_input("New Price", value=txn_row['price'], key="upd_price")
        new_date = st.date_input("New Date", value=pd.to_datetime(txn_row['date']), key="upd_date")

        if st.button("Update Transaction"):
            c.execute("UPDATE transactions SET quantity = ?, price = ?, date = ? WHERE transaction_id = ?",
                      (new_qty, new_price, new_date, selected_txn_id))
            conn.commit()
            st.success("Transaction updated.")
            st.experimental_rerun()

        if st.button("Delete Transaction"):
            c.execute("DELETE FROM transactions WHERE transaction_id = ?", (selected_txn_id,))
            conn.commit()
            st.warning("Transaction deleted.")
            st.experimental_rerun()

    st.subheader("📢 Set Price Alerts")
    a_stock = st.text_input("Stock Symbol (for alert)", key="alert")
    tgt = st.number_input("Target Price", 0.0, key="target")
    sl = st.number_input("Stop Loss", 0.0, key="stoploss")
    if st.button("Save Alert"):
        c.execute("INSERT INTO alerts (client_name, stock_name, target_price, stop_loss_price) VALUES (?, ?, ?, ?)",
                  (selected_client, a_stock, tgt, sl))
        conn.commit()
        st.success("Alert saved!")

    st.subheader("🚨 Active Alerts")
    df_alerts = pd.read_sql("SELECT * FROM alerts WHERE client_name = ?", conn, params=(selected_client,))
    for _, row in df_alerts.iterrows():
        price = get_current_price(row['stock_name'])
        if price:
            if row['target_price'] and price >= row['target_price']:
                st.error(f"🎯 {row['stock_name']} hit target ₹{row['target_price']} (Now ₹{price})")
            if row['stop_loss_price'] and price <= row['stop_loss_price']:
                st.warning(f"🔻 {row['stock_name']} hit stop loss ₹{row['stop_loss_price']} (Now ₹{price})")

    st.subheader("📈 Portfolio Insights")
    realized, realized_df = calculate_realized_profit(selected_client)
    unreal_df, unrealized, invested = calculate_unrealized_profit(selected_client)

    st.markdown(f"### 💸 Realized Profit/Loss: ₹{realized:,.2f}")
    if not realized_df.empty:
        st.dataframe(realized_df.style.format({"Realized Profit": "₹{:.2f}"}))

    if not unreal_df.empty:
        st.markdown("### 💼 Current Holdings")
        st.dataframe(unreal_df.style.format({
            "Average Buy Price": "₹{:.2f}",
            "Current Market Price": "₹{:.2f}",
            "Unrealized Profit/Loss": "₹{:.2f}",
            "Valuation": "₹{:.2f}"
        }))

        st.subheader("🥧 Holdings by Value")
        fig, ax = plt.subplots()
        pie_data = unreal_df.set_index("Stock Name")["Valuation"]
        ax.pie(pie_data, labels=pie_data.index,
               autopct=lambda p: f'{p:.1f}%\n₹{p*pie_data.sum()/100:,.0f}',
               startangle=90)
        ax.axis("equal")
        st.pyplot(fig)
    else:
        st.warning("No current holdings.")

    client_row = pd.read_sql("SELECT * FROM clients WHERE client_name = ?", conn, params=(selected_client,))
    if 'initial_cash' in client_row.columns and not client_row.empty:
        initial_cash = client_row['initial_cash'].iloc[0]
    else:
        initial_cash = 0.0
    net_value = realized + unrealized + invested
    net_profit = net_value - initial_cash
    net_pct = (net_profit / initial_cash) * 100 if initial_cash > 0 else 0

    st.subheader("💰 Financial Summary")
    st.markdown(f"""
- 🏦 **Initial Cash**: ₹{initial_cash:,.2f}  
- 💸 **Cash Deployed**: ₹{invested:,.2f}  
- 📈 **Net Portfolio Value**: ₹{net_value:,.2f}  
- 💹 **Total Profit/Loss**: ₹{net_profit:,.2f} ({net_pct:+.2f}%)
""")
# Updated code combining portfolio tracker and downloadable PDF report with pie chart and Rs. format


from fpdf import FPDF
from io import BytesIO
import os
from datetime import datetime


def get_realized_profit_df(client):
    df = pd.read_sql("SELECT * FROM transactions WHERE client_name = ?", conn, params=(client,))
    profits = []
    for stock in df['stock_name'].unique():
        buys = df[(df['stock_name'] == stock) & (df['transaction_type'] == 'Buy')]
        sells = df[(df['stock_name'] == stock) & (df['transaction_type'] == 'Sell')]
        if not sells.empty and not buys.empty:
            avg = (buys['quantity'] * buys['price']).sum() / buys['quantity'].sum()
            profit = ((sells['price'] - avg) * sells['quantity']).sum()
            profits.append({"Stock Name": stock, "Realized Profit": round(profit, 2)})
    return pd.DataFrame(profits)

def calculate_unrealized_profit(client):
    df = pd.read_sql("SELECT * FROM transactions WHERE client_name = ?", conn, params=(client,))
    rows = []
    unrealized = invested = 0
    for stock in df['stock_name'].unique():
        buys = df[(df['stock_name'] == stock) & (df['transaction_type'] == 'Buy')]
        sells = df[(df['stock_name'] == stock) & (df['transaction_type'] == 'Sell')]
        qty = buys['quantity'].sum() - sells['quantity'].sum()
        if qty > 0:
            avg = (buys['quantity'] * buys['price']).sum() / buys['quantity'].sum()
            current = get_current_price(stock)
            if current:
                value = current * qty
                pl = (current - avg) * qty
                unrealized += pl
                invested += avg * qty
                rows.append({
                    "Stock Name": stock,
                    "Average Buy Price": round(avg, 2),
                    "Current Market Price": current,
                    "Quantity Held": qty,
                    "Unrealized Profit/Loss": round(pl, 2),
                    "Valuation": round(value, 2)
                })
    return pd.DataFrame(rows), round(unrealized, 2), round(invested, 2)

# PDF generation
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "Portfolio Performance Report", ln=True, align="C")
        self.set_font("Arial", "", 10)
        self.cell(0, 10, f"Generated on: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}", ln=True, align="C")
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

def generate_pdf(client, realized_df, unreal_df, initial_cash, invested, net_value, net_profit, net_pct):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Financial Summary
    pdf.multi_cell(0, 8, f"Client: {client}\n\nFinancial Summary:\n- Initial Cash: Rs. {initial_cash:,.2f}\n- Cash Deployed: Rs. {invested:,.2f}\n- Net Portfolio Value: Rs. {net_value:,.2f}\n- Realized P&L: Rs. {realized_df['Realized Profit'].sum():,.2f}\n- Unrealized P&L: Rs. {net_value - invested - realized_df['Realized Profit'].sum():,.2f}\n- Net P&L: Rs. {net_profit:,.2f} ({net_pct:+.2f}%)")

    # Realized Profit Table
    if not realized_df.empty:
        pdf.ln(8)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Realized Profit (Stock-wise)", ln=True)


        pdf.set_font("Arial", "B", 11)
        pdf.cell(90, 8, "Stock Name", border=1, align="C")
        pdf.cell(50, 8, "Realized Profit (Rs.)", border=1, align="C")
        pdf.ln()

        pdf.set_font("Arial", "", 11)
        for _, row in realized_df.iterrows():
            pdf.cell(90, 8, str(row["Stock Name"]), border=1)
            pdf.cell(50, 8, f'{row["Realized Profit"]:,.2f}', border=1, align="R")
            pdf.ln()

    # Unrealized Holdings Table
    if not unreal_df.empty:
        pdf.ln(8)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Current Holdings", ln=True)

        headers = ["Stock", "Qty", "Buy Price", "CMP", "P/L", "Valuation"]
        col_widths = [40, 15, 25, 25, 25, 30]

        pdf.set_font("Arial", "B", 10)
        for i, h in enumerate(headers):
            pdf.cell(col_widths[i], 8, h, border=1, align="C")
        pdf.ln()

        pdf.set_font("Arial", "", 10)
        for _, row in unreal_df.iterrows():
            pdf.cell(col_widths[0], 8, str(row["Stock Name"]), border=1)
            pdf.cell(col_widths[1], 8, str(row["Quantity Held"]), border=1, align="C")
            pdf.cell(col_widths[2], 8, f'{row["Average Buy Price"]:,.2f}', border=1, align="R")
            pdf.cell(col_widths[3], 8, f'{row["Current Market Price"]:,.2f}', border=1, align="R")
            pdf.cell(col_widths[4], 8, f'{row["Unrealized Profit/Loss"]:,.2f}', border=1, align="R")
            pdf.cell(col_widths[5], 8, f'{row["Valuation"]:,.2f}', border=1, align="R")
            pdf.ln()

        # Pie Chart
        fig, ax = plt.subplots()
        pie_data = unreal_df.set_index("Stock Name")["Valuation"]
        ax.pie(pie_data, labels=pie_data.index, autopct='%1.1f%%', startangle=90)
        ax.axis("equal")
        chart_path = f"{client}_pie_chart.png"
        fig.savefig(chart_path)
        plt.close(fig)
        pdf.image(chart_path, w=180)
        os.remove(chart_path)

    # Finalize PDF
    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

# App UI


if selected_client:
    realized_df = get_realized_profit_df(selected_client)
    unreal_df, unrealized, invested = calculate_unrealized_profit(selected_client)
    client_row = pd.read_sql("SELECT * FROM clients WHERE client_name = ?", conn, params=(selected_client,))
    initial_cash = client_row['initial_cash'].iloc[0] if not client_row.empty else 0.0
    realized_total = realized_df['Realized Profit'].sum() if not realized_df.empty else 0
    net_value = realized_total + unrealized + invested
    net_profit = net_value - initial_cash
    net_pct = (net_profit / initial_cash) * 100 if initial_cash > 0 else 0


    if not realized_df.empty:
        st.subheader("📈 Realized Profit")
        st.dataframe(realized_df)


    if st.button("📄 Generate PDF Report"):
        pdf = generate_pdf(selected_client, realized_df, unreal_df, initial_cash, invested, net_value, net_profit, net_pct)
        st.download_button("⬇️ Download Report", data=pdf, file_name=f"{selected_client}_report.pdf", mime="application/pdf")
