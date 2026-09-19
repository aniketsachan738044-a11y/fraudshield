from io import BytesIO
from datetime import datetime, timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.models import Transaction, User
from app.services.fraud_engine import fraud_engine


def generate_executive_fraud_pdf(user: User, transactions: list[Transaction]) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a'),
        fontName='Helvetica-Bold',
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#64748b'),
        fontName='Helvetica',
    )
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#1e293b'),
        fontName='Helvetica-Bold',
        spaceBefore=12,
        spaceAfter=6,
    )
    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#334155'),
        fontName='Helvetica',
    )
    cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=cell_style,
        fontName='Helvetica-Bold',
    )

    story = []

    # 1. Header Banner
    story.append(Paragraph('FraudShield AI &mdash; Executive Risk & Compliance Report', title_style))
    now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    story.append(
        Paragraph(
            f'<b>Generated:</b> {now_str} &nbsp;|&nbsp; <b>Account:</b> {user.email} (ID: {user.id}) &nbsp;|&nbsp; <b>Compliance Status:</b> ACTIVE',
            subtitle_style,
        )
    )
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width='100%', thickness=1.5, color=colors.HexColor('#2563eb'), spaceAfter=14))

    # 2. Executive KPIs
    total_count = len(transactions)
    total_volume = sum(tx.amount for tx in transactions)
    high_risk_count = sum(1 for tx in transactions if tx.risk_level == 'high')
    med_risk_count = sum(1 for tx in transactions if tx.risk_level == 'medium')
    low_risk_count = sum(1 for tx in transactions if tx.risk_level == 'low')
    avg_score = (sum(tx.risk_score for tx in transactions) / total_count) if total_count > 0 else 0.0

    kpi_data = [
        [
            Paragraph('<b>Audited Events</b>', cell_style),
            Paragraph('<b>Audited Volume</b>', cell_style),
            Paragraph('<b>High Risk Flags</b>', cell_style),
            Paragraph('<b>Review Required</b>', cell_style),
            Paragraph('<b>Low Risk Allowed</b>', cell_style),
            Paragraph('<b>Mean Risk Score</b>', cell_style),
        ],
        [
            Paragraph(f'<font size=13 color="#0f172a"><b>{total_count}</b></font>', cell_style),
            Paragraph(f'<font size=13 color="#0f172a"><b>INR {total_volume:,.2f}</b></font>', cell_style),
            Paragraph(f'<font size=13 color="#dc2626"><b>{high_risk_count}</b></font>', cell_style),
            Paragraph(f'<font size=13 color="#d97706"><b>{med_risk_count}</b></font>', cell_style),
            Paragraph(f'<font size=13 color="#16a34a"><b>{low_risk_count}</b></font>', cell_style),
            Paragraph(f'<font size=13 color="#0f172a"><b>{avg_score:.1f}/100</b></font>', cell_style),
        ],
    ]
    kpi_table = Table(kpi_data, colWidths=[80, 120, 85, 85, 85, 85])
    kpi_table.setStyle(
        TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ])
    )
    story.append(kpi_table)
    story.append(Spacer(1, 14))

    # 3. Transaction Audit Trail
    story.append(Paragraph('Detailed Transaction Ledger & Risk Decision Log', section_style))

    ledger_headers = ['ID', 'Timestamp', 'Amount', 'Channel', 'Counterparty', 'Location', 'Risk', 'Action', 'Primary Indicator']
    ledger_rows = [
        [Paragraph(f'<font color="white"><b>{h}</b></font>', cell_bold) for h in ledger_headers]
    ]

    for tx in transactions[:60]:
        reasons = fraud_engine.explanations_from_json(tx.explanation_json)
        top_reason = reasons[0].title if reasons else 'Normal transaction'
        if len(top_reason) > 28:
            top_reason = top_reason[:26] + '...'

        badge_color = '#dc2626' if tx.risk_level == 'high' else ('#d97706' if tx.risk_level == 'medium' else '#16a34a')
        date_str = tx.created_at.strftime('%m-%d %H:%M') if tx.created_at else 'N/A'
        city_str = tx.location_city or 'Unknown'

        ledger_rows.append([
            Paragraph(str(tx.id), cell_style),
            Paragraph(date_str, cell_style),
            Paragraph(f'INR {tx.amount:,.0f}', cell_style),
            Paragraph(tx.channel, cell_style),
            Paragraph(tx.receiver_id[:12], cell_style),
            Paragraph(city_str, cell_style),
            Paragraph(f'<font color="{badge_color}"><b>{tx.risk_score:.0f}</b> ({tx.risk_level})</font>', cell_style),
            Paragraph(tx.recommendation.upper(), cell_style),
            Paragraph(top_reason, cell_style),
        ])

    ledger_table = Table(
        ledger_rows,
        colWidths=[25, 55, 65, 50, 70, 60, 65, 50, 100],
    )
    ledger_table.setStyle(
        TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ])
    )

    story.append(ledger_table)

    story.append(Spacer(1, 14))
    story.append(
        Paragraph(
            '<i>Confidential Document. Generated by FraudShield Enterprise ML & Real-Time Rule Engine. For compliance and internal fraud investigation only.</i>',
            subtitle_style,
        )
    )

    doc.build(story)
    buffer.seek(0)
    return buffer