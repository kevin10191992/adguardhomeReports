#!/usr/bin/env python3
"""
AdGuard Home Daily Report Generator
Main orchestrator: fetches query logs, analyzes per-client, generates PDFs, emails reports.
"""

import os
import sys
import logging
from datetime import datetime

from dotenv import load_dotenv

# Load .env file if present (useful for local development; Docker injects env vars directly)
load_dotenv()

from config import Config
from adguard_client import AdGuardClient
from data_analyzer import DataAnalyzer
from domain_classifier import DomainClassifier
from report_generator import ReportGenerator
from email_sender import EmailSender

logger = logging.getLogger(__name__)


def main():
    # --- 1. Configuration ---
    config = Config()
    config.setup_logging()
    logger.info('=' * 60)
    logger.info('AdGuard Home Report Generator - Iniciando')
    logger.info('=' * 60)

    # --- 2. Connect to AdGuard Home ---
    client = AdGuardClient(config.adguard_url, config.adguard_user, config.adguard_pass)
    if not client.test_connection():
        logger.error('No se pudo conectar a AdGuard Home. Abortando.')
        sys.exit(1)

    # --- 3. Get named clients ---
    clients_data = client.get_clients()
    named_clients = clients_data.get('clients', [])

    if not named_clients:
        logger.warning('No se encontraron clientes nombrados en AdGuard Home.')
        logger.info('Configura clientes con nombres en AdGuard Home > Configuración > Clientes.')
        sys.exit(0)

    logger.info(f'Clientes nombrados encontrados: {len(named_clients)}')
    for c in named_clients:
        logger.info(f'  - {c.get("name", "?")} ({", ".join(c.get("ids", []))})')

    # --- 4. Fetch ALL query logs for the configured period ---
    logger.info(f'Descargando query log de las últimas {config.querylog_hours} horas...')
    all_logs = client.get_all_querylog(
        hours=config.querylog_hours,
        limit_per_page=config.querylog_limit,
    )
    logger.info(f'Total de entradas obtenidas: {len(all_logs)}')

    if not all_logs:
        logger.warning('No se obtuvieron registros del query log. Abortando.')
        sys.exit(0)

    # --- 5. Analyze and generate reports ---
    analyzer = DataAnalyzer()
    classifier = DomainClassifier()
    report_gen = ReportGenerator(config.reports_dir)

    report_date = datetime.now().strftime('%Y-%m-%d')
    generated_pdfs = []
    total_queries_all = 0
    total_blocked_all = 0

    for client_info in named_clients:
        client_name = client_info.get('name', 'Unknown')
        client_ids = client_info.get('ids', [])

        logger.info(f'--- Procesando cliente: {client_name} ---')

        # Filter logs for this client
        # IDs can be IPs or Client IDs (e.g., MAC, hostname)
        client_ips = [cid for cid in client_ids]
        client_logs = analyzer.filter_by_client(all_logs, client_ips, client_ids)

        if not client_logs:
            logger.info(f'  Sin actividad para {client_name}. Saltando.')
            continue

        logger.info(f'  Entradas encontradas: {len(client_logs)}')

        # Run full analysis
        summary = analyzer.get_summary(client_logs)
        top_domains = analyzer.get_top_domains(client_logs, n=config.top_domains_count)
        top_blocked = analyzer.get_top_blocked(client_logs, n=config.top_domains_count)
        hourly = analyzer.get_hourly_distribution(client_logs)
        query_types = analyzer.get_query_types(client_logs)
        blocking_summary = analyzer.get_blocking_summary(client_logs)
        response_times = analyzer.get_response_times(client_logs)
        upstreams = analyzer.get_upstream_stats(client_logs)
        risk = analyzer.calculate_risk_score(client_logs)

        # Classify domains into categories
        all_domains = analyzer.get_top_domains(client_logs, n=500)  # Get more for classification
        categories = classifier.classify_bulk(all_domains)

        # Compile analysis results
        analysis = {
            'summary': summary,
            'top_domains': top_domains,
            'top_blocked': top_blocked,
            'hourly': hourly,
            'query_types': query_types,
            'blocking_summary': blocking_summary,
            'response_times': response_times,
            'upstreams': upstreams,
            'risk': risk,
            'categories': categories,
        }

        # Generate PDF
        try:
            pdf_path = report_gen.generate(
                client_name=client_name,
                client_ips=client_ids,
                report_date=report_date,
                analysis=analysis,
            )
            generated_pdfs.append(pdf_path)
            total_queries_all += summary.get('total_queries', 0)
            total_blocked_all += summary.get('blocked_queries', 0)
            logger.info(f'  ✅ PDF generado: {pdf_path}')
        except Exception as e:
            logger.error(f'  ❌ Error generando PDF para {client_name}: {e}', exc_info=True)

    # --- 6. Send email with all reports ---
    if generated_pdfs:
        logger.info(f'Enviando {len(generated_pdfs)} informe(s) por email...')
        try:
            email_sender = EmailSender(
                api_key=config.resend_api_key,
                from_email=config.email_from,
                to_emails=config.email_to,
            )
            block_pct = round(total_blocked_all / total_queries_all * 100, 1) if total_queries_all > 0 else 0
            summary_data = {
                'total_queries': total_queries_all,
                'total_blocked': total_blocked_all,
                'block_percentage': block_pct,
            }
            result = email_sender.send_reports(generated_pdfs, report_date, summary_data)
            logger.info(f'✅ Email enviado exitosamente. ID: {result.get("id", "N/A")}')
        except Exception as e:
            logger.error(f'❌ Error enviando email: {e}', exc_info=True)
    else:
        logger.warning('No se generaron PDFs. No se envía email.')

    # --- 7. Summary ---
    logger.info('=' * 60)
    logger.info(f'Resumen de ejecución:')
    logger.info(f'  Clientes procesados: {len(generated_pdfs)}/{len(named_clients)}')
    logger.info(f'  Total consultas: {total_queries_all:,}')
    logger.info(f'  Total bloqueadas: {total_blocked_all:,}')
    logger.info(f'  PDFs generados: {len(generated_pdfs)}')
    logger.info('=' * 60)
    logger.info('Finalizado.')


if __name__ == '__main__':
    main()
