import os
import logging
from datetime import datetime

import resend

logger = logging.getLogger(__name__)


class EmailSender:
    """Sends report emails with PDF attachments via Resend API."""

    def __init__(self, api_key: str, from_email: str, to_emails: list[str]):
        resend.api_key = api_key
        self.from_email = from_email
        self.to_emails = to_emails

    def send_reports(self, pdf_paths: list[str], report_date: str, summary_data: dict = None) -> dict:
        """Send a single email with all PDF reports as attachments.
        
        Args:
            pdf_paths: List of absolute paths to PDF files
            report_date: Date string for the report (YYYY-MM-DD)
            summary_data: Optional summary statistics for the email body
        
        Returns:
            Resend API response dict
        """
        if not pdf_paths:
            logger.warning('No PDF files to send.')
            return {}

        attachments = []
        for path in pdf_paths:
            if not os.path.exists(path):
                logger.warning(f'PDF file not found, skipping: {path}')
                continue
            with open(path, 'rb') as f:
                attachments.append({
                    'filename': os.path.basename(path),
                    'content': list(f.read()),
                })

        if not attachments:
            logger.error('No valid PDF attachments found.')
            return {}

        html_body = self._build_html(pdf_paths, report_date, summary_data)

        params = {
            'from': self.from_email,
            'to': self.to_emails,
            'subject': f'\U0001f4ca Informes AdGuard Home - {report_date}',
            'html': html_body,
            'attachments': attachments,
        }

        try:
            result = resend.Emails.send(params)
            logger.info(f'Email enviado exitosamente a {self.to_emails}. ID: {result.get("id", "N/A")}')
            return result
        except Exception as e:
            logger.error(f'Error enviando email: {e}')
            raise

    def _build_html(self, pdf_paths: list[str], report_date: str, summary_data: dict = None) -> str:
        """Build the HTML email body with a summary."""
        client_count = len(pdf_paths)
        client_names = [os.path.basename(p).replace('.pdf', '').replace(f'_{report_date}', '').replace('Informe_', '') for p in pdf_paths]

        summary_rows = ''
        if summary_data:
            total_queries = summary_data.get('total_queries', 0)
            total_blocked = summary_data.get('total_blocked', 0)
            block_pct = summary_data.get('block_percentage', 0)
            summary_rows = f'''
            <tr>
                <td style="padding: 8px 16px; color: #555;">Total consultas DNS</td>
                <td style="padding: 8px 16px; font-weight: bold; text-align: right;">{total_queries:,}</td>
            </tr>
            <tr style="background: #f9f9f9;">
                <td style="padding: 8px 16px; color: #555;">Consultas bloqueadas</td>
                <td style="padding: 8px 16px; font-weight: bold; text-align: right; color: #e53935;">{total_blocked:,} ({block_pct}%)</td>
            </tr>
            '''

        clients_list = ''.join(f'<li style="padding: 4px 0; color: #333;">{name}</li>' for name in client_names)

        return f'''
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 0; background: #f5f5f5;">
            <div style="max-width: 600px; margin: 20px auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #67b279 0%, #4a9a5c 100%); padding: 32px 24px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">\U0001f6e1\ufe0f AdGuard Home</h1>
                    <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0; font-size: 16px;">Informes Diarios de Actividad DNS</p>
                </div>

                <!-- Content -->
                <div style="padding: 24px;">
                    <p style="color: #333; font-size: 15px;">Se han generado <strong>{client_count}</strong> informe(s) correspondientes al <strong>{report_date}</strong>.</p>

                    <!-- Summary Table -->
                    <table style="width: 100%; border-collapse: collapse; margin: 16px 0; border: 1px solid #e0e0e0; border-radius: 8px;">
                        <tr style="background: #f0f7f1;">
                            <td colspan="2" style="padding: 10px 16px; font-weight: bold; color: #4a9a5c;">\U0001f4c8 Resumen General</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 16px; color: #555;">Clientes analizados</td>
                            <td style="padding: 8px 16px; font-weight: bold; text-align: right;">{client_count}</td>
                        </tr>
                        {summary_rows}
                    </table>

                    <!-- Client List -->
                    <p style="color: #555; font-size: 14px; margin-top: 20px;"><strong>Clientes incluidos:</strong></p>
                    <ul style="margin: 8px 0; padding-left: 20px;">
                        {clients_list}
                    </ul>

                    <p style="color: #888; font-size: 13px; margin-top: 24px; padding-top: 16px; border-top: 1px solid #eee;">Los informes detallados en PDF est\u00e1n adjuntos a este email.</p>
                </div>

                <!-- Footer -->
                <div style="background: #f9f9f9; padding: 16px 24px; text-align: center;">
                    <p style="color: #aaa; font-size: 12px; margin: 0;">Generado autom\u00e1ticamente por AdGuard Home Report Generator</p>
                </div>
            </div>
        </body>
        </html>
        '''
