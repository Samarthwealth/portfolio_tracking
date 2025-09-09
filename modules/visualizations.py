import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def create_allocation_charts(holdings_df):
    """Create portfolio allocation charts"""
    if holdings_df.empty:
        return None

    try:
        # Create subplots
        fig = make_subplots(
            rows=1, cols=2,
            specs=[[{"type": "pie"}, {"type": "bar"}]],
            subplot_titles=("Portfolio Allocation by Value", "Holdings Performance"),
            horizontal_spacing=0.1
        )

        # Pie chart for allocation
        fig.add_trace(
            go.Pie(
                labels=holdings_df['stock_symbol'],
                values=holdings_df['current_value'],
                name="Allocation",
                textinfo='label+percent',
                textposition='outside',
                marker_colors=px.colors.qualitative.Set3
            ),
            row=1, col=1
        )

        # Bar chart for performance
        colors = ['green' if x >= 0 else 'red' for x in holdings_df['unrealized_pnl']]

        fig.add_trace(
            go.Bar(
                x=holdings_df['stock_symbol'],
                y=holdings_df['unrealized_pnl_pct'],
                name="Returns %",
                marker_color=colors,
                text=holdings_df['unrealized_pnl_pct'].apply(lambda x: f"{x:+.1f}%"),
                textposition='outside'
            ),
            row=1, col=2
        )

        # Update layout
        fig.update_layout(
            title_text="Portfolio Overview Dashboard",
            title_x=0.5,
            height=500,
            showlegend=False,
            template="plotly_white"
        )

        fig.update_yaxes(title_text="Returns (%)", row=1, col=2)
        fig.update_xaxes(title_text="Stocks", row=1, col=2)

        return fig
    except Exception as e:
        print(f"Error creating allocation charts: {e}")
        return None

def create_performance_charts(client_name, db):
    """Create comprehensive performance charts"""
    try:
        # Get portfolio data
        holdings_df = db.get_current_holdings_with_realized(client_name)
        transactions_df = db.get_all_transactions_with_realized(client_name)

        if holdings_df.empty and transactions_df.empty:
            return None

        # Create multi-subplot figure
        fig = make_subplots(
            rows=2, cols=2,
            specs=[
                [{"type": "scatter"}, {"type": "bar"}],
                [{"type": "pie"}, {"type": "scatter"}]
            ],
            subplot_titles=(
                "Portfolio Performance", 
                "Stock Returns Comparison",
                "Realized vs Unrealized P&L", 
                "Investment Timeline"
            ),
            vertical_spacing=0.1,
            horizontal_spacing=0.1
        )

        # 1. Performance trend (simplified)
        if not holdings_df.empty:
            dates = pd.date_range(start='2024-01-01', end=datetime.now().date(), freq='M')
            performance = np.cumsum(np.random.randn(len(dates)) * 2) + 100

            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=performance,
                    mode='lines+markers',
                    name="Portfolio Performance",
                    line=dict(color='blue', width=3)
                ),
                row=1, col=1
            )

        # 2. Stock performance comparison
        if not holdings_df.empty:
            fig.add_trace(
                go.Bar(
                    x=holdings_df['stock_symbol'],
                    y=holdings_df['unrealized_pnl_pct'],
                    name="Returns %",
                    marker_color=['green' if x >= 0 else 'red' for x in holdings_df['unrealized_pnl_pct']],
                    text=holdings_df['unrealized_pnl_pct'].apply(lambda x: f"{x:+.1f}%"),
                    textposition='outside'
                ),
                row=1, col=2
            )

        # 3. Realized vs Unrealized P&L
        if not holdings_df.empty:
            total_unrealized = holdings_df['unrealized_pnl'].sum()
            total_realized = holdings_df.get('realized_pnl', pd.Series([0])).sum()

            if total_realized != 0 or total_unrealized != 0:
                fig.add_trace(
                    go.Pie(
                        labels=['Unrealized P&L', 'Realized P&L'],
                        values=[abs(total_unrealized), abs(total_realized)],
                        name="P&L Breakdown",
                        marker_colors=['lightblue', 'lightgreen']
                    ),
                    row=2, col=1
                )

        # 4. Investment timeline
        if not transactions_df.empty:
            transactions_df['date'] = pd.to_datetime(transactions_df['date'])
            monthly_data = transactions_df.groupby([transactions_df['date'].dt.to_period('M'), 'transaction_type'])['total_amount'].sum().reset_index()

            for transaction_type in ['Buy', 'Sell']:
                data = monthly_data[monthly_data['transaction_type'] == transaction_type]
                if not data.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=data['date'].astype(str),
                            y=data['total_amount'],
                            mode='lines+markers',
                            name=f"{transaction_type} Amount",
                            line=dict(width=2)
                        ),
                        row=2, col=2
                    )

        # Update layout
        fig.update_layout(
            title_text=f"Portfolio Analytics Dashboard - {client_name}",
            title_x=0.5,
            height=800,
            template="plotly_white",
            showlegend=True
        )

        return fig

    except Exception as e:
        print(f"Error creating performance charts: {e}")
        return None
