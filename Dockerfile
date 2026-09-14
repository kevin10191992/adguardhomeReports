FROM python:3.12-slim

# System dependencies for Matplotlib and cron
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    libfreetype6-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY config.py .
COPY main.py .
COPY adguard_client.py .
COPY data_analyzer.py .
COPY domain_classifier.py .
COPY report_generator.py .
COPY email_sender.py .
COPY entrypoint.sh .

RUN chmod +x entrypoint.sh

# Create directories for reports and logs
RUN mkdir -p /app/reports /app/logs

# Set matplotlib to use non-interactive backend and cache dir
ENV MPLBACKEND=Agg
ENV MPLCONFIGDIR=/tmp/matplotlib

ENTRYPOINT ["/app/entrypoint.sh"]
