from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import Color, black, blue, green, red, grey
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib import colors
from io import BytesIO
from datetime import datetime
import pandas as pd
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

# Register the font with ReportLab
pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
def generate_advanced_pdf(client_name, db, report_type, report_period, include_charts=True):
    """Generate professional PDF report"""
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )

        # Container for the 'Flowable' objects
        elements = []

        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.darkblue
        )

        # Title page
        elements.append(Paragraph(f"Portfolio Report", title_style))
        elements.append(Paragraph(f"Client: {client_name}", styles['Heading2']))
        elements.append(Paragraph(f"Report Type: {report_type}", styles['Normal']))
        elements.append(Paragraph(f"Period: {report_period}", styles['Normal']))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
        elements.append(Spacer(1, 30))

        # Executive Summary
        elements.append(Paragraph("Executive Summary", heading_style))

        # Get portfolio data
        portfolio_summary = db.get_portfolio_summary(client_name)
        cash_balance = db.get_cash_balance(client_name)
        realized_profits = db.get_total_realized_profit(client_name)
        client_data = db.get_client_data(client_name)

        initial_cash = client_data[2] if client_data else 0
        total_portfolio_value = cash_balance + portfolio_summary.get('current_value', 0)
        total_returns = realized_profits + portfolio_summary.get('total_pnl', 0)
        total_return_pct = (total_returns / initial_cash * 100) if initial_cash > 0 else 0

        def format_currency(amount):
            if amount >= 10000000:
                return f"₹{amount/10000000:.2f} Cr"
            elif amount >= 100000:
                return f"₹{amount/100000:.2f} L"
            else:
                return f"₹{amount:,.2f}"

        summary_style = ParagraphStyle(
            'SummaryStyle',
            parent=styles['Normal'],
            fontName='DejaVuSans',  # Use your registered font that supports ₹
            fontSize=11,
            leading=14,
            spaceAfter=12,
        )

        summary_text = f"""
        Your portfolio has achieved a total return of {format_currency(total_returns)} ({total_return_pct:+.2f}%) 
        on an initial investment of {format_currency(initial_cash)}. The current portfolio value stands at 
        {format_currency(total_portfolio_value)}, including {format_currency(cash_balance)} in cash and 
        {format_currency(portfolio_summary.get('current_value', 0))} in equity investments.

        You have realized profits of {format_currency(realized_profits)} from selling positions, while 
        your current holdings show unrealized gains of {format_currency(portfolio_summary.get('total_pnl', 0))}.
        """

        elements.append(Paragraph(summary_text, summary_style))
        elements.append(Spacer(1, 20))

        # Key Metrics Table
        elements.append(Paragraph("Key Portfolio Metrics", heading_style))

        metrics_data = [
            ['Metric', 'Value', 'Metric', 'Value'],
            ['Initial Investment', format_currency(initial_cash), 'Cash Balance', format_currency(cash_balance)],
            ['Invested Amount', format_currency(portfolio_summary.get('invested_amount', 0)), 'Current Portfolio Value', format_currency(portfolio_summary.get('current_value', 0))],
            ['Total Portfolio Value', format_currency(total_portfolio_value), 'Unrealized P&L', format_currency(portfolio_summary.get('total_pnl', 0))],
            ['Realized P&L', format_currency(realized_profits), 'Total P&L', format_currency(total_returns)],
            ['Total Return %', f"{total_return_pct:+.2f}%", 'Risk Profile', client_data[3] if client_data and len(client_data) > 3 else 'Not Set']
        ]

        metrics_table = Table(metrics_data, colWidths=[2*inch, 1.5*inch, 2*inch, 1.5*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        elements.append(metrics_table)
        elements.append(Spacer(1, 20))

        # Current Holdings
        holdings_df = db.get_current_holdings_with_realized(client_name)
        if not holdings_df.empty:
            elements.append(Paragraph("Current Holdings", heading_style))

            # Holdings table
            holdings_data = [['Stock', 'Qty', 'Avg Price', 'Current Price', 'Value', 'Unrealized P&L', 'Realized P&L']]

            for _, row in holdings_df.iterrows():
                holdings_data.append([
                    row['stock_symbol'],
                    str(int(row['quantity'])),
                    f"₹{row['avg_price']:,.0f}",
                    f"₹{row['current_price']:,.0f}",
                    f"₹{row['current_value']:,.0f}",
                    f"₹{row['unrealized_pnl']:,.0f}",
                    f"₹{row.get('realized_pnl', 0):,.0f}"
                ])

            # Total row
            holdings_data.append([
                'TOTAL',
                str(int(holdings_df['quantity'].sum())),
                '',
                '',
                f"₹{holdings_df['current_value'].sum():,.0f}",
                f"₹{holdings_df['unrealized_pnl'].sum():,.0f}",
                f"₹{holdings_df.get('realized_pnl', pd.Series([0])).sum():,.0f}"
            ])

            holdings_table = Table(holdings_data, colWidths=[1*inch, 0.6*inch, 0.8*inch, 1.2*inch, 1*inch, 1.2*inch, 1.2*inch])
            holdings_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('FONTNAME', (0, -1), (-1, -1), 'DejaVuSans'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            elements.append(holdings_table)
            elements.append(Spacer(1, 20))

        # Footer information
        elements.append(Spacer(1, 30))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER,
            textColor=colors.grey
        )

        elements.append(Paragraph("Generated by Advanced Portfolio Management System Pro", footer_style))
        elements.append(Paragraph(f"Report Date: {datetime.now().strftime('%B %d, %Y')}", footer_style))

        # Build PDF
        doc.build(elements)

        # Get the value of the BytesIO buffer and return it
        pdf_bytes = buffer.getvalue()
        buffer.close()

        return pdf_bytes

    except Exception as e:
        print(f"Error generating PDF report: {e}")
        return None
