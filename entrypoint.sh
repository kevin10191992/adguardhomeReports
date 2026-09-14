#!/bin/bash
set -e

echo "=============================================="
echo " AdGuard Home Report Generator"
echo " Starting container..."
echo "=============================================="

# --- Validate required environment variables ---
REQUIRED_VARS="ADGUARD_URL ADGUARD_USER ADGUARD_PASS RESEND_API_KEY EMAIL_FROM EMAIL_TO"
for var in $REQUIRED_VARS; do
    if [ -z "${!var}" ]; then
        echo "ERROR: Variable de entorno requerida no definida: $var"
        exit 1
    fi
done

# --- Setup cron schedule ---
CRON_SCHEDULE="${CRON_SCHEDULE:-0 6 * * *}"
echo "Cron schedule: $CRON_SCHEDULE"
echo "Timezone: ${TZ:-UTC}"

# Export all environment variables to a file so cron can access them
printenv | grep -v "no_proxy" > /etc/environment

# Create the cron job
# The cron job sources /etc/environment to get env vars, then runs main.py
echo "${CRON_SCHEDULE} root . /etc/environment; cd /app && /usr/local/bin/python main.py >> /app/logs/cron.log 2>&1" > /etc/cron.d/adguard-reports
chmod 0644 /etc/cron.d/adguard-reports
crontab /etc/cron.d/adguard-reports

echo "Cron job configurado: ${CRON_SCHEDULE}"

# --- Run immediately on start if configured ---
RUN_ON_START="${RUN_ON_START:-true}"
if [ "$RUN_ON_START" = "true" ]; then
    echo "Ejecutando generación de informes inicial..."
    cd /app && python main.py 2>&1 | tee /app/logs/initial_run.log
    echo "Ejecución inicial completada."
fi

echo "=============================================="
echo " Cron activo. Esperando próxima ejecución..."
echo " Schedule: ${CRON_SCHEDULE}"
echo "=============================================="

# Start cron in foreground
cron -f
