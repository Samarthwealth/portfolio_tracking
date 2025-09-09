from datetime import datetime
import pandas as pd
import numpy as np

def format_currency(amount: float) -> str:
    """Format currency with Indian formatting"""
    if amount is None:
        return "₹0.00"

    if amount >= 10000000:  # 1 crore
        return f"₹{amount/10000000:.2f} Cr"
    elif amount >= 100000:  # 1 lakh
        return f"₹{amount/100000:.2f} L"
    else:
        return f"₹{amount:,.2f}"

def calculate_returns(initial_value: float, current_value: float) -> tuple:
    """Calculate absolute and percentage returns"""
    if initial_value == 0:
        return 0, 0

    absolute_return = current_value - initial_value
    percentage_return = (absolute_return / initial_value) * 100

    return absolute_return, percentage_return

def calculate_cagr(initial_value: float, final_value: float, years: float) -> float:
    """Calculate Compound Annual Growth Rate"""
    if initial_value <= 0 or final_value <= 0 or years <= 0:
        return 0

    cagr = ((final_value / initial_value) ** (1/years)) - 1
    return cagr * 100

def get_financial_year(date_str: str) -> str:
    """Get financial year from date string"""
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
        if date.month >= 4:  # April onwards
            return f"FY{date.year}-{date.year + 1}"
        else:
            return f"FY{date.year - 1}-{date.year}"
    except:
        return "Unknown"

def generate_portfolio_insights(df: pd.DataFrame) -> list:
    """Generate portfolio insights and recommendations"""
    insights = []

    if df.empty:
        return ["No holdings found. Consider adding some investments to your portfolio."]

    # Check concentration risk
    total_value = df['current_value'].sum()
    max_holding_pct = (df['current_value'].max() / total_value * 100) if total_value > 0 else 0

    if max_holding_pct > 30:
        insights.append(f"⚠️ Concentration risk: Your largest holding represents {max_holding_pct:.1f}% of portfolio")

    # Check diversification
    if len(df) < 5:
        insights.append("📈 Consider diversifying with more holdings (recommended: 8-12 stocks)")
    elif len(df) > 20:
        insights.append("📊 You have many holdings. Consider consolidating for better management")

    # Performance insights
    winners = df[df['unrealized_pnl'] > 0]
    losers = df[df['unrealized_pnl'] < 0]

    if len(winners) > len(losers):
        insights.append(f"✅ Good performance: {len(winners)} profitable vs {len(losers)} loss-making positions")
    elif len(losers) > len(winners):
        insights.append(f"⚠️ Review needed: {len(losers)} loss-making vs {len(winners)} profitable positions")

    return insights

def format_date(date_str: str) -> str:
    """Format date string for display"""
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
        return date.strftime('%d %b %Y')
    except:
        return date_str

def format_percentage(value: float) -> str:
    """Format percentage with proper sign"""
    if value >= 0:
        return f"+{value:.2f}%"
    else:
        return f"{value:.2f}%"
