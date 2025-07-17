# portfolio_app.py
import streamlit as st
import pandas as pd
import yfinance as yf
import sqlite3
import threading
import matplotlib.pyplot as plt
import os
from fpdf import FPDF
from io import BytesIO
from datetime import datetime
import numpy as np
from contextlib import contextmanager

###############################################################################
# DATABASE  (WAL + global write lock)
###############################################################################
_LOCK = threading.Lock()

@st.cache_resource
def get_conn():
    conn = sqlite3.connect("portfolio.db", timeout=20.0, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS clients (
            client_id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT UNIQUE,
            initial_cash REAL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            stock_name TEXT,
            transaction_type TEXT,
            quantity INTEGER,
            price REAL,
            date TEXT);
        CREATE TABLE IF NOT EXISTS alerts (
            alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            stock_name TEXT,
            target_price REAL,
            stop_loss_price REAL);
        CREATE TABLE IF NOT EXISTS ledger (
            ledger_id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            date TEXT,
            description TEXT,
            amount REAL);
    """)
    conn.commit()
    return conn


###############################################################################
# ATOMIC WRITE  (global lock)
###############################################################################
@contextmanager
def _atomic_write():
    """Ensure only one worker writes at a time."""
    with _LOCK:
        conn = get_conn()
        conn.execute("BEGIN")
        try:
            yield conn
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise


def safe_insert(sql: str, params: tuple):
    with _atomic_write() as conn:
        conn.execute(sql, params)


###############################################################################
# HELPERS
###############################################################################
@st.cache_data(ttl=300)
def get_current_price(symbol: str) -> float | None:
    try:
        ticker = yf.Ticker(symbol + ".NS")
        data = ticker.history(period="5d")
        last_valid = data["Close"].dropna().iloc[-1]
        return round(float(last_valid), 2)
    except Exception:
        return None


def add_ledger_entry(client, date, description, amount):
    safe_insert(
        "INSERT INTO ledger (client_name, date, description, amount) VALUES (?,?,?,?)",
        (client, str(date), description, round(amount, 2)),
    )


def get_ledger_balance(client):
    df = pd.read_sql(
        "SELECT amount FROM ledger WHERE client_name = ?", get_conn(), params=(client,)
    )
    return round(df["amount"].sum(), 2) if not df.empty else 0.0


###############################################################################
# LEDGER UI
###############################################################################
def show_ledger(client):
    st.subheader("📒 Ledger Entries")
    df = pd.read_sql(
        "SELECT * FROM ledger WHERE client_name = ? ORDER BY date DESC",
        get_conn(),
        params=(client,),
    )
    if df.empty:
        st.info("No ledger entries.")
        return

    st.markdown(f"**Ledger Balance**: Rs. {df['amount'].sum():,.2f}")

    for _, row in df.iterrows():
        key = f"{client}_{row['ledger_id']}"
        with st.expander(f"{row['date']} – {row['description']} (Rs. {row['amount']:,.2f})"):
            new_date = st.date_input(
                "Date", pd.to_datetime(row["date"]), key=f"date_{key}"
            )
            new_desc = st.text_input(
                "Description", row["description"], key=f"desc_{key}", max_chars=50
            )
            new_amt = st.number_input(
                "Amount", value=float(row["amount"]), key=f"amt_{key}"
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✏️ Update", key=f"upd_{key}"):
                    safe_insert(
                        "UPDATE ledger SET date=?, description=?, amount=? WHERE ledger_id=?",
                        (str(new_date), new_desc, round(new_amt, 2), row["ledger_id"]),
                    )
                    st.toast("✅ Entry updated")
                    st.rerun()
            with col2:
                if st.button("🗑️ Delete", key=f"del_{key}"):
                    safe_insert("DELETE FROM ledger WHERE ledger_id=?", (row["ledger_id"],))
                    st.toast("🗑️ Entry deleted")
                    st.rerun()


def add_ledger_form(client):
    st.subheader("➕ Add Ledger Entry")
    with st.form(key=f"add_ledger_{client}", clear_on_submit=True):
        date = st.date_input("Date")
        desc = st.text_input("Description", max_chars=50)
        amt = st.number_input("Amount", step=100.0)
        if st.form_submit_button("Add Entry"):
            add_ledger_entry(client, date, desc, amt)
            st.toast("✅ Entry added")
            st.rerun()


###############################################################################
# SIDEBAR
###############################################################################
st.sidebar.header("👤 Client Management")
with st.sidebar.form("add_client_form", clear_on_submit=True):
    new_name = st.text_input("Client Name", max_chars=30)
    new_cash = st.number_input("Initial Cash", min_value=0.0, value=100_000.0)
    if st.form_submit_button("Add Client"):
        try:
            safe_insert(
                "INSERT INTO clients (client_name, initial_cash) VALUES (?,?)",
                (new_name, new_cash),
            )
            add_ledger_entry(new_name, datetime.today().date(), "Initial Deposit", new_cash)
            st.toast("✅ Client created")
            st.rerun()
        except sqlite3.IntegrityError:
            st.sidebar.error("Client already exists.")

clients = pd.read_sql(
    "SELECT client_name FROM clients ORDER BY client_name", get_conn()
)["client_name"].tolist()
if clients:
    del_client = st.sidebar.selectbox("Delete Client", clients, key="del_select")
    if st.sidebar.button("Delete", key="del_client_btn"):
        if st.sidebar.checkbox("Confirm delete?"):
            for tbl in ["clients", "transactions", "alerts", "ledger"]:
                safe_insert(f"DELETE FROM {tbl} WHERE client_name=?", (del_client,))
            st.toast("🗑️ Client deleted")
            st.rerun()

###############################################################################
# MAIN
###############################################################################
st.title("📊 Stock Portfolio Tracker")
if not clients:
    st.stop()
selected = st.selectbox("Select Client", clients)

###############################################################################
# LEDGER
###############################################################################
show_ledger(selected)
add_ledger_form(selected)

###############################################################################
# TRANSACTIONS
###############################################################################
st.header(f"📥 Add Transaction for {selected}")
with st.form("add_txn", clear_on_submit=True):
    stock = st.text_input("Stock Symbol", max_chars=10).upper()
    ttype = st.radio("Type", ["Buy", "Sell"], horizontal=True)
    qty = st.number_input("Quantity", min_value=1, step=1)
    price = st.number_input("Price", min_value=0.0, step=0.05)
    date = st.date_input("Date")
    if st.form_submit_button("Add Transaction"):
        safe_insert(
            "INSERT INTO transactions (client_name, stock_name, transaction_type, quantity, price, date) VALUES (?,?,?,?,?,?)",
            (selected, stock, ttype, qty, round(price, 2), date),
        )
        if ttype == "Sell":
            df_txn_all = pd.read_sql(
                "SELECT * FROM transactions WHERE client_name=? AND stock_name=?",
                get_conn(),
                params=(selected, stock),
            )
            buys = df_txn_all[df_txn_all["transaction_type"] == "Buy"]
            avg_cost = (
                (buys["quantity"] * buys["price"]).sum() / buys["quantity"].sum()
                if not buys.empty
                else 0.0
            )
            proceeds = qty * price
            add_ledger_entry(selected, date, f"Sell {stock} {qty}@", proceeds)
            add_ledger_entry(selected, date, f"COGS {stock} {qty}@", -round(avg_cost * qty, 2))
        st.toast("✅ Transaction saved")
        st.rerun()

df_txn = pd.read_sql(
    "SELECT * FROM transactions WHERE client_name=?", get_conn(), params=(selected,)
)
if not df_txn.empty:
    st.subheader("📃 Transaction History")
    st.dataframe(df_txn, use_container_width=True)
    tid = st.selectbox("Edit/Delete Txn ID", df_txn["transaction_id"], key="txn_select")
    txn = df_txn[df_txn["transaction_id"] == tid].iloc[0]
    new_qty = st.number_input("Qty", value=int(txn["quantity"]), key="ed_qty")
    new_price = st.number_input("Price", value=float(txn["price"]), key="ed_price")
    new_date = st.date_input("Date", value=pd.to_datetime(txn["date"]), key="ed_date")
    if st.button("Update Transaction", key=f"upd_txn_{tid}"):
        safe_insert(
            "UPDATE transactions SET quantity=?, price=?, date=? WHERE transaction_id=?",
            (new_qty, round(new_price, 2), new_date, tid),
        )
        st.toast("✅ Transaction updated")
        st.rerun()
    if st.button("Delete Transaction", type="secondary", key=f"del_txn_{tid}"):
        safe_insert("DELETE FROM transactions WHERE transaction_id=?", (tid,))
        st.toast("🗑️ Transaction deleted")
        st.rerun()

###############################################################################
# ALERTS
###############################################################################
st.subheader("📢 Price Alerts")
with st.form("add_alert", clear_on_submit=True):
    a_stock = st.text_input("Stock", max_chars=10).upper()
    tgt = st.number_input("Target", min_value=0.0, step=0.05)
    sl = st.number_input("Stop-loss", min_value=0.0, step=0.05)
    if st.form_submit_button("Save Alert"):
        safe_insert(
            "INSERT INTO alerts (client_name, stock_name, target_price, stop_loss_price) VALUES (?,?,?,?)",
            (selected, a_stock, round(tgt, 2), round(sl, 2)),
        )
        st.toast("✅ Alert saved")
        st.rerun()

df_alerts = pd.read_sql(
    "SELECT * FROM alerts WHERE client_name=?", get_conn(), params=(selected,)
)
for _, r in df_alerts.iterrows():
    p = get_current_price(r["stock_name"])
    if p:
        if r["target_price"] and p >= r["target_price"]:
            st.error(f"🎯 {r['stock_name']} hit target Rs. {r['target_price']} (now Rs. {p})")
        if r["stop_loss_price"] and p <= r["stop_loss_price"]:
            st.warning(f"🔻 {r['stock_name']} hit stop-loss Rs. {r['stop_loss_price']} (now Rs. {p})")

###############################################################################
# INSIGHTS (FIFO)  – unchanged
###############################################################################
# calc_profits is exactly as given earlier
realized_df, unreal_df, realized, unreal, invested = calc_profits(selected)
ledger_balance = get_ledger_balance(selected)
net_value = invested + realized + unreal
net_pl = realized + unreal
net_pct = (net_pl / ledger_balance * 100) if ledger_balance else 0
cash = ledger_balance - invested

_fmt = lambda x: f"Rs. {x:,.2f}"

st.subheader("📈 Portfolio Insights")
col1, col2 = st.columns(2)
col1.metric("Ledger Balance", _fmt(ledger_balance))
col1.metric("Invested", _fmt(invested))
col1.metric("Cash Available", _fmt(cash))
col2.metric("Net Portfolio Value", _fmt(net_value))
col2.metric("Realized P&L", _fmt(realized))
col2.metric("Unrealized P&L", _fmt(unreal))
st.metric("Total P&L", f"{_fmt(net_pl)} ({net_pct:+.2f}%)")

if not unreal_df.empty:
    st.subheader("💼 Holdings")
    st.dataframe(
        unreal_df.style.format({c: _fmt for c in ["Avg", "CMP", "P&L", "Value"]}),
        use_container_width=True,
    )
    fig, ax = plt.subplots()
    ax.pie(
        unreal_df["Value"],
        labels=unreal_df["Stock"],
        autopct=lambda pct: f"{pct:.1f}%\n{_fmt(pct / 100 * unreal_df['Value'].sum())}",
        startangle=90,
    )
    ax.axis("equal")
    st.pyplot(fig)

###############################################################################
# PDF  – unchanged
###############################################################################
class PDF(FPDF):
    def __init__(self):
        super().__init__(orientation="L")
        self.set_left_margin(4)
        self.set_right_margin(4)

    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "Portfolio Report", ln=True, align="C")
        self.set_font("Helvetica", "", 10)
        self.cell(0, 8, f"Generated: {datetime.now():%d-%m-%Y}", ln=True, align="C")
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def generate_pdf(client, r_df, u_df, ledger, invested, realized, unreal):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    net_profit = realized + unreal
    net_pct = (net_profit / ledger * 100) if ledger else 0
    summary = (
        f"Client: {client}\n\n"
        f"Ledger Balance (Cash In): Rs. {ledger:,.2f}\n"
        f"Cash Deployed (Invested): Rs. {invested:,.2f}\n"
        f"Current Cash Available: Rs. {ledger - invested:,.2f}\n"
        f"Net Portfolio Value: Rs. {invested + realized + unreal:,.2f}\n"
        f"Realized P&L: Rs. {realized:,.2f}\n"
        f"Unrealized P&L: Rs. {unreal:,.2f}\n"
        f"Total Profit/Loss: Rs. {net_profit:,.2f} ({net_pct:+.2f}%)"
    )
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 5, summary)
    pdf.ln(3)

    def table(df, title, headers, rel_widths):
        if df.empty:
            return
        usable = pdf.w - pdf.l_margin - pdf.r_margin
        abs_widths = [usable * r / sum(rel_widths) for r in rel_widths]

        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 6, title, ln=True)
        pdf.set_font("Helvetica", "B", 9)

        for h, w in zip(headers, abs_widths):
            pdf.cell(w, 5, str(h), border=1, align="C")
        pdf.ln()
        pdf.set_font("Helvetica", "", 9)

        float_cols = df.select_dtypes(include=[np.number]).columns
        for _, row in df.iterrows():
            for val, w in zip(row, abs_widths):
                if val in float_cols or isinstance(val, (float, np.number)):
                    val = f"{float(val):.2f}"
                pdf.cell(w, 5, str(val), border=1)
            pdf.ln()

        if title == "Holdings" and not df.empty:
            totals = {
                "Stock": "Total",
                "Qty": str(int(df["Qty"].sum())),
                "Avg": "",
                "CMP": "",
                "P&L": f"{df['P&L'].sum():.2f}",
                "Value": f"{df['Value'].sum():.2f}",
            }
            pdf.set_font("Helvetica", "B", 9)
            for key, w in zip(headers, abs_widths):
                v = totals.get(key, "")
                pdf.cell(w, 5, str(v), border=1, align="C")
            pdf.ln()

    table(r_df, "Realized P&L", ["Stock", "P&L"], [3, 1])
    if not u_df.empty:
        table(
            u_df,
            "Holdings",
            ["Stock", "Qty", "Avg", "CMP", "P&L", "Value"],
            [2, 1, 1.5, 1.5, 1.5, 1.5],
        )
        pdf.ln(6)
        try:
            fig, ax = plt.subplots(figsize=(3.5, 3), dpi=200)
            ax.pie(u_df["Value"], labels=u_df["Stock"], autopct="%1.1f%%", startangle=90)
            ax.axis("equal")
            fname = f"{client}_pie.png"
            fig.savefig(fname, bbox_inches="tight")
            plt.close(fig)
            pdf.image(fname, w=pdf.w / 2.8)
            os.remove(fname)
        except Exception:
            pass

    buffer = BytesIO()
    buffer.write(pdf.output(dest="S"))
    buffer.seek(0)
    return buffer


if st.button("📄 Generate PDF Report"):
    buf = generate_pdf(selected, realized_df, unreal_df, ledger_balance, invested, realized, unreal)
    st.download_button(
        "⬇️ Download Report",
        data=buf,
        file_name=f"{selected}_report.pdf",
        mime="application/pdf",
    )
