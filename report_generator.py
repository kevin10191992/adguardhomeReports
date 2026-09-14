import io
import os
import logging
import tempfile
from datetime import datetime

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.figure import Figure

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable,
)
from reportlab.graphics.shapes import Drawing, Line

logger = logging.getLogger(__name__)

# Color scheme
COLOR_PRIMARY = '#4a9a5c'       # AdGuard green
COLOR_SECONDARY = '#67b279'
COLOR_DANGER = '#e53935'         # Red for blocked
COLOR_WARNING = '#f9a825'        # Yellow
COLOR_INFO = '#1e88e5'           # Blue
COLOR_BG_LIGHT = '#f0f7f1'       # Light green bg

# Chart color palette
CHART_COLORS = [
    '#4a9a5c', '#1e88e5', '#e53935', '#f9a825', '#8e24aa',
    '#00acc1', '#ff7043', '#5c6bc0', '#26a69a', '#ec407a',
    '#78909c', '#d4e157', '#ab47bc', '#29b6f6', '#ef5350',
    '#66bb6a', '#ffa726', '#42a5f5', '#7e57c2', '#26c6da',
]


class ReportGenerator:
    """Generates professional PDF reports for AdGuard Home clients."""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        """Setup custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Title'],
            fontSize=28,
            textColor=colors.HexColor(COLOR_PRIMARY),
            spaceAfter=6,
        ))
        self.styles.add(ParagraphStyle(
            name='ReportSubtitle',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#666666'),
            spaceAfter=20,
            alignment=TA_CENTER,
        ))
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor(COLOR_PRIMARY),
            spaceBefore=20,
            spaceAfter=10,
            borderWidth=0,
            borderPadding=0,
        ))
        self.styles.add(ParagraphStyle(
            name='StatLabel',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#888888'),
        ))
        self.styles.add(ParagraphStyle(
            name='StatValue',
            parent=self.styles['Normal'],
            fontSize=20,
            textColor=colors.HexColor('#333333'),
            fontName='Helvetica-Bold',
        ))
        self.styles.add(ParagraphStyle(
            name='SmallText',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#aaaaaa'),
        ))

    def generate(self, client_name: str, client_ips: list[str],
                 report_date: str, analysis: dict) -> str:
        """Generate a PDF report for a client.
        
        Args:
            client_name: Human readable client name
            client_ips: List of IPs for this client
            report_date: Date string YYYY-MM-DD
            analysis: Dict with all analysis results from DataAnalyzer
        
        Returns:
            Path to the generated PDF file
        """
        # Create date subdirectory
        date_dir = os.path.join(self.output_dir, report_date)
        os.makedirs(date_dir, exist_ok=True)

        # Sanitize filename
        safe_name = client_name.replace(' ', '_').replace('/', '-').replace('\\', '-')
        filename = f'Informe_{safe_name}_{report_date}.pdf'
        filepath = os.path.join(date_dir, filename)

        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
        )

        elements = []
        self._add_cover(elements, client_name, client_ips, report_date)
        elements.append(PageBreak())
        self._add_summary(elements, analysis.get('summary', {}))
        self._add_hourly_chart(elements, analysis.get('hourly', {}))
        self._add_top_domains(elements, analysis.get('top_domains', []))
        self._add_blocked_domains(elements, analysis.get('top_blocked', []))
        self._add_categories(elements, analysis.get('categories', {}))
        self._add_query_types(elements, analysis.get('query_types', []))
        self._add_security(elements, analysis.get('risk', {}), analysis.get('blocking_summary', {}))
        self._add_performance(elements, analysis.get('response_times', {}), analysis.get('upstreams', []))

        # Footer
        elements.append(Spacer(1, 30))
        elements.append(HRFlowable(width='100%', color=colors.HexColor('#e0e0e0')))
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(
            f'Informe generado autom\u00e1ticamente el {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} por AdGuard Home Report Generator',
            self.styles['SmallText'],
        ))

        doc.build(elements)
        logger.info(f'PDF generated: {filepath}')
        return filepath

    # --- Cover Page ---
    def _add_cover(self, elements, client_name, client_ips, report_date):
        elements.append(Spacer(1, 2 * inch))
        elements.append(Paragraph('\U0001f6e1\ufe0f', ParagraphStyle(
            'emoji', parent=self.styles['Title'], fontSize=48, alignment=TA_CENTER,
        )))
        elements.append(Paragraph('AdGuard Home', self.styles['ReportTitle']))
        elements.append(Paragraph('Informe de Actividad DNS', self.styles['ReportSubtitle']))
        elements.append(Spacer(1, 40))

        # Client info box
        info_data = [
            ['Cliente', client_name],
            ['IP(s)', ', '.join(client_ips)],
            ['Fecha', report_date],
            ['Per\u00edodo', '\u00daltimas 24 horas'],
        ]
        info_table = Table(info_data, colWidths=[1.5 * inch, 4 * inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor(COLOR_BG_LIGHT)),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor(COLOR_PRIMARY)),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('PADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(info_table)

    # --- Executive Summary ---
    def _add_summary(self, elements, summary):
        elements.append(Paragraph('\U0001f4ca Resumen Ejecutivo', self.styles['SectionTitle']))
        elements.append(HRFlowable(width='100%', color=colors.HexColor(COLOR_PRIMARY), thickness=2))
        elements.append(Spacer(1, 12))

        total = summary.get('total_queries', 0)
        blocked = summary.get('blocked_queries', 0)
        allowed = summary.get('allowed_queries', 0)
        block_pct = summary.get('block_percentage', 0)
        avg_h = summary.get('avg_per_hour', 0)

        stats_data = [
            ['Total Consultas', 'Bloqueadas', 'Permitidas', '% Bloqueo', 'Prom/Hora'],
            [f'{total:,}', f'{blocked:,}', f'{allowed:,}', f'{block_pct}%', f'{avg_h}'],
        ]
        stats_table = Table(stats_data, colWidths=[1.3 * inch] * 5)
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(COLOR_PRIMARY)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, 1), 16),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('PADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('TEXTCOLOR', (1, 1), (1, 1), colors.HexColor(COLOR_DANGER)),
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 12))

    # --- Hourly Distribution Chart ---
    def _add_hourly_chart(self, elements, hourly):
        elements.append(Paragraph('\U0001f4c8 Actividad por Hora', self.styles['SectionTitle']))
        elements.append(HRFlowable(width='100%', color=colors.HexColor(COLOR_PRIMARY), thickness=2))
        elements.append(Spacer(1, 8))

        if not hourly:
            elements.append(Paragraph('Sin datos disponibles.', self.styles['Normal']))
            return

        hours = list(range(24))
        totals = [hourly.get(h, {}).get('total', 0) for h in hours]
        blocked = [hourly.get(h, {}).get('blocked', 0) for h in hours]

        fig, ax = plt.subplots(figsize=(7, 2.8))
        bar_width = 0.4
        x_pos = range(24)
        ax.bar([x - bar_width/2 for x in x_pos], totals, bar_width, label='Total', color=COLOR_PRIMARY, alpha=0.8)
        ax.bar([x + bar_width/2 for x in x_pos], blocked, bar_width, label='Bloqueadas', color=COLOR_DANGER, alpha=0.8)
        ax.set_xlabel('Hora del d\u00eda', fontsize=9)
        ax.set_ylabel('Consultas', fontsize=9)
        ax.set_xticks(range(24))
        ax.set_xticklabels([f'{h:02d}' for h in range(24)], fontsize=7)
        ax.legend(fontsize=8)
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()

        img = self._fig_to_image(fig, width=6.5 * inch, height=2.6 * inch)
        elements.append(img)
        elements.append(Spacer(1, 12))

        # Peak hour
        if totals:
            peak_h = totals.index(max(totals))
            elements.append(Paragraph(
                f'<b>Hora pico:</b> {peak_h:02d}:00 con {max(totals):,} consultas',
                self.styles['Normal'],
            ))
        elements.append(Spacer(1, 8))

    # --- Top Domains Table ---
    def _add_top_domains(self, elements, top_domains):
        elements.append(Paragraph('\U0001f310 Top Dominios M\u00e1s Consultados', self.styles['SectionTitle']))
        elements.append(HRFlowable(width='100%', color=colors.HexColor(COLOR_PRIMARY), thickness=2))
        elements.append(Spacer(1, 8))

        if not top_domains:
            elements.append(Paragraph('Sin datos disponibles.', self.styles['Normal']))
            return

        # Pie chart for top 10
        top10 = top_domains[:10]
        labels = [d[0][:30] for d in top10]
        sizes = [d[1] for d in top10]

        fig, ax = plt.subplots(figsize=(5, 3))
        wedges, texts, autotexts = ax.pie(
            sizes, labels=None, autopct='%1.0f%%',
            colors=CHART_COLORS[:len(sizes)], startangle=90,
            pctdistance=0.8, textprops={'fontsize': 7},
        )
        ax.legend(labels, loc='center left', bbox_to_anchor=(1, 0.5), fontsize=7)
        plt.tight_layout()

        img = self._fig_to_image(fig, width=6.5 * inch, height=3 * inch)
        elements.append(img)
        elements.append(Spacer(1, 8))

        # Table
        header = ['#', 'Dominio', 'Consultas']
        data = [header]
        for i, (domain, count) in enumerate(top_domains, 1):
            data.append([str(i), domain[:50], f'{count:,}'])

        table = self._make_table(data, col_widths=[0.4 * inch, 4.5 * inch, 1.5 * inch])
        elements.append(table)
        elements.append(Spacer(1, 12))

    # --- Blocked Domains ---
    def _add_blocked_domains(self, elements, top_blocked):
        elements.append(Paragraph('\U0001f6ab Top Dominios Bloqueados', self.styles['SectionTitle']))
        elements.append(HRFlowable(width='100%', color=colors.HexColor(COLOR_PRIMARY), thickness=2))
        elements.append(Spacer(1, 8))

        if not top_blocked:
            elements.append(Paragraph('No se registraron bloqueos en este per\u00edodo. \u2705', self.styles['Normal']))
            return

        header = ['#', 'Dominio', 'Raz\u00f3n', 'Intentos']
        data = [header]
        for i, (domain, reason, count) in enumerate(top_blocked, 1):
            data.append([str(i), domain[:40], reason[:20], f'{count:,}'])

        table = self._make_table(data, col_widths=[0.4 * inch, 3 * inch, 1.8 * inch, 1.2 * inch])
        elements.append(table)
        elements.append(Spacer(1, 12))

    # --- Categories ---
    def _add_categories(self, elements, categories):
        elements.append(Paragraph('\U0001f3f7\ufe0f Clasificaci\u00f3n por Categor\u00edas', self.styles['SectionTitle']))
        elements.append(HRFlowable(width='100%', color=colors.HexColor(COLOR_PRIMARY), thickness=2))
        elements.append(Spacer(1, 8))

        if not categories:
            elements.append(Paragraph('Sin datos disponibles.', self.styles['Normal']))
            return

        # Sort by count
        sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        labels = [c[0] for c in sorted_cats]
        sizes = [c[1] for c in sorted_cats]

        fig, ax = plt.subplots(figsize=(5, 3.2))
        wedges, texts, autotexts = ax.pie(
            sizes, labels=None, autopct='%1.0f%%',
            colors=CHART_COLORS[:len(sizes)], startangle=90,
            pctdistance=0.8, textprops={'fontsize': 7},
        )
        ax.legend(labels, loc='center left', bbox_to_anchor=(1, 0.5), fontsize=7)
        plt.tight_layout()

        img = self._fig_to_image(fig, width=6.5 * inch, height=3 * inch)
        elements.append(img)
        elements.append(Spacer(1, 8))

        # Table
        header = ['Categor\u00eda', 'Consultas', 'Porcentaje']
        data = [header]
        total = sum(sizes)
        for cat, count in sorted_cats:
            pct = round(count / total * 100, 1) if total > 0 else 0
            data.append([cat, f'{count:,}', f'{pct}%'])

        table = self._make_table(data, col_widths=[3 * inch, 1.8 * inch, 1.6 * inch])
        elements.append(table)
        elements.append(Spacer(1, 12))

    # --- Query Types ---
    def _add_query_types(self, elements, query_types):
        elements.append(Paragraph('\U0001f4c9 Tipos de Consulta DNS', self.styles['SectionTitle']))
        elements.append(HRFlowable(width='100%', color=colors.HexColor(COLOR_PRIMARY), thickness=2))
        elements.append(Spacer(1, 8))

        if not query_types:
            elements.append(Paragraph('Sin datos disponibles.', self.styles['Normal']))
            return

        labels = [qt[0] for qt in query_types]
        values = [qt[1] for qt in query_types]

        fig, ax = plt.subplots(figsize=(6, max(2, len(labels) * 0.35)))
        y_pos = range(len(labels))
        ax.barh(y_pos, values, color=CHART_COLORS[:len(values)], height=0.6)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=9)
        ax.set_xlabel('Consultas', fontsize=9)
        ax.invert_yaxis()
        ax.grid(axis='x', alpha=0.3)
        for i, v in enumerate(values):
            ax.text(v + max(values) * 0.01, i, f'{v:,}', va='center', fontsize=8)
        plt.tight_layout()

        height = max(2, len(labels) * 0.35) * inch
        img = self._fig_to_image(fig, width=6.5 * inch, height=min(height, 4 * inch))
        elements.append(img)
        elements.append(Spacer(1, 12))

    # --- Security Summary ---
    def _add_security(self, elements, risk, blocking_summary):
        elements.append(Paragraph('\U0001f512 Resumen de Seguridad', self.styles['SectionTitle']))
        elements.append(HRFlowable(width='100%', color=colors.HexColor(COLOR_PRIMARY), thickness=2))
        elements.append(Spacer(1, 8))

        # Risk indicator
        level = risk.get('level', 'Sin datos')
        score = risk.get('score', 0)
        elements.append(Paragraph(f'<b>Nivel de riesgo:</b> {level} (Puntuaci\u00f3n: {score}/100)', self.styles['Normal']))
        elements.append(Spacer(1, 8))

        # Threat details
        details = risk.get('details', {})
        if details:
            header = ['Tipo de Amenaza', 'Detecciones']
            data = [header]
            threat_labels = {
                'malware': '\U0001f6a8 Malware / Phishing',
                'phishing': '\U0001f3a3 Phishing',
                'parental': '\U0001f46a Control Parental',
                'adblock': '\U0001f6ab Publicidad / Trackers',
            }
            for key, count in details.items():
                label = threat_labels.get(key, key)
                data.append([label, f'{count:,}'])
            table = self._make_table(data, col_widths=[4.5 * inch, 1.9 * inch])
            elements.append(table)
            elements.append(Spacer(1, 8))

        # Blocking summary
        if blocking_summary:
            elements.append(Paragraph('<b>Bloqueos por tipo de filtro:</b>', self.styles['Normal']))
            elements.append(Spacer(1, 4))
            header = ['Filtro', 'Bloqueos']
            data = [header]
            for reason, count in blocking_summary.items():
                data.append([reason, f'{count:,}'])
            table = self._make_table(data, col_widths=[4.5 * inch, 1.9 * inch])
            elements.append(table)
        elements.append(Spacer(1, 12))

    # --- Performance ---
    def _add_performance(self, elements, response_times, upstreams):
        elements.append(Paragraph('\u23f1\ufe0f Rendimiento', self.styles['SectionTitle']))
        elements.append(HRFlowable(width='100%', color=colors.HexColor(COLOR_PRIMARY), thickness=2))
        elements.append(Spacer(1, 8))

        # Response times
        if response_times and response_times.get('avg_ms', 0) > 0:
            header = ['M\u00e9trica', 'Valor']
            data = [
                header,
                ['Tiempo promedio', f'{response_times["avg_ms"]} ms'],
                ['Tiempo m\u00ednimo', f'{response_times["min_ms"]} ms'],
                ['Tiempo m\u00e1ximo', f'{response_times["max_ms"]} ms'],
                ['Mediana', f'{response_times["median_ms"]} ms'],
            ]
            table = self._make_table(data, col_widths=[4.5 * inch, 1.9 * inch])
            elements.append(table)
            elements.append(Spacer(1, 12))

        # Upstreams
        if upstreams:
            elements.append(Paragraph('<b>Servidores DNS Upstream m\u00e1s utilizados:</b>', self.styles['Normal']))
            elements.append(Spacer(1, 4))
            header = ['Upstream', 'Consultas']
            data = [header]
            for upstream, count in upstreams:
                data.append([upstream, f'{count:,}'])
            table = self._make_table(data, col_widths=[4.5 * inch, 1.9 * inch])
            elements.append(table)

    # --- Utility Methods ---
    def _fig_to_image(self, fig, width, height) -> Image:
        """Convert a matplotlib figure to a ReportLab Image."""
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        buf.seek(0)
        return Image(buf, width=width, height=height)

    def _make_table(self, data, col_widths=None) -> Table:
        """Create a styled table with zebra stripes."""
        table = Table(data, colWidths=col_widths, repeatRows=1)
        style = [
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(COLOR_PRIMARY)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            # Body
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ]
        # Zebra stripes
        for i in range(1, len(data)):
            if i % 2 == 0:
                style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f9f9f9')))
        table.setStyle(TableStyle(style))
        return table
