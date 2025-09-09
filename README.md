# Advanced Portfolio Tracker Pro 📊

A comprehensive portfolio management system built with Streamlit that provides professional-grade portfolio tracking, cash management, realized profit calculations, and detailed reporting capabilities.

## 🚀 Features

### Core Functionality
- **💰 Realized Profit Tracking**: FIFO-based calculations for accurate profit tracking
- **🏦 Complete Cash Management**: Track deposits, withdrawals, and cash flows
- **📊 Professional Reports**: Generate PDF and Excel reports with charts
- **📈 Real-time Analytics**: Interactive dashboards with live stock prices
- **👥 Multi-Client Support**: Manage multiple portfolios seamlessly
- **📥 Bulk Import**: Excel file import with validation
- **🗑️ Client Management**: Add and delete clients with all associated data

### Advanced Features
- **Complete Ledger System**: Unified view of all transactions
- **Realized vs Unrealized P&L**: Separate tracking of both profit types
- **Interactive Charts**: Plotly-based visualizations
- **Professional Reports**: PDF and Excel export functionality
- **Cash Flow Analysis**: Detailed cash movement tracking
- **Portfolio Analytics**: Performance metrics and insights

## 🛠️ Installation

1. **Extract the project files**
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the application**:
   ```bash
   streamlit run app.py
   ```

## 💻 Usage

### Getting Started
1. **Add a Client**: Use the sidebar to add a new client
2. **Add Transactions**: Input buy/sell transactions manually or via Excel
3. **Manage Cash**: Track deposits, withdrawals, and cash flows
4. **View Analytics**: Analyze performance with interactive charts
5. **Generate Reports**: Create professional PDF and Excel reports

### Key Features

#### 📈 Dashboard
- Real-time portfolio metrics
- Cash balance and investment values
- Realized vs unrealized P&L breakdown
- Current holdings with performance analysis

#### 💰 Cash Management
- Add deposits and withdrawals
- Complete cash transaction history
- Cash flow analysis and statistics
- Automatic cash updates from trading

#### 📥 Upload Data
- Bulk Excel file import
- Data validation and error checking
- Sample template download
- Progress tracking during import

#### 🎯 Transactions
- Manual transaction entry
- Complete transaction history
- Advanced filtering options
- Realized profit calculations

#### 📊 Analytics
- Interactive performance charts
- Portfolio insights and metrics
- Risk analysis and recommendations
- Performance comparison tools

#### 📄 Reports
- Professional PDF reports
- Detailed Excel workbooks
- Multiple report types
- Charts and visualizations included

#### 📋 Ledger
- Complete transaction ledger
- Unified view of all activities
- Running balance calculations
- Flexible filtering options

## 📊 Realized Profit Calculation

The system uses **FIFO (First In, First Out)** method:
- Buy transactions are queued chronologically
- Sell transactions match against oldest purchases first
- Accurate profit calculation for tax reporting
- Complete audit trail of all transactions

## 🔐 Security & Privacy

- **Local Storage**: All data stored locally in SQLite
- **No Cloud Dependencies**: Runs entirely on your machine
- **Data Privacy**: Financial data never leaves your device
- **Easy Backup**: Simple SQLite database file

## 🎯 Technical Specifications

- **Frontend**: Streamlit with custom CSS
- **Backend**: Python with SQLite database
- **Charts**: Plotly for interactive visualizations
- **Reports**: ReportLab (PDF) + OpenPyXL (Excel)
- **Data Source**: Yahoo Finance API for real-time prices

## 📞 Support

- **Email**: support@portfoliopro.com
- **Phone**: +91-XXXXX-XXXXX

---

**Built with ❤️ using Streamlit, Plotly, and Python**
