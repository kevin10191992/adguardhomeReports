# 🛡️ AdGuard Home Daily Reports

Generador automatizado de informes de actividad DNS en PDF por cliente para **AdGuard Home**, con análisis de comportamiento, categorización de tráfico, métricas de seguridad y despacho por correo electrónico mediante **Resend**. Diseñado especialmente para entornos **Homelab** y contenedores Docker.

---

## 🎯 ¿Para qué sirve este proyecto?

AdGuard Home ofrece estadísticas globales excelentes, pero es difícil obtener un desglose profundo y periódico de **qué hace cada cliente o dispositivo nombrado en tu red**.

Este proyecto resuelve ese problema:
- 🕒 **Job programado diario (Cron):** Se ejecuta automáticamente a la hora que configures.
- 👤 **Informes individuales por cliente:** Extrae los registros de cada cliente nombrado en AdGuard Home y genera un informe PDF exclusivo para cada uno.
- 📊 **Métricas detalladas:** Dominios más visitados, dominios y servicios bloqueados, distribución de actividad por hora, tipos de consulta DNS y servidores upstream utilizados.
- 🏷️ **Clasificación por categorías:** Agrupa el tráfico automáticamente en 13 categorías (Redes Sociales, Streaming Video/Música, Gaming, Productividad, Telemetría, etc.).
- 🚨 **Evaluación de amenazas y riesgo:** Calcula un nivel de riesgo analizando bloqueos por malware, phishing y control parental.
- 📧 **Entrega por email (Resend):** Envía un correo con resumen ejecutivo en HTML y todos los PDFs adjuntos.
- 🐳 **100% Dockerizado:** Compatible con arquitecturas `amd64` (PC / Servidor / Proxmox) y `arm64` (Raspberry Pi / mini PCs).

---

## 🏗️ ¿Cómo funciona la arquitectura?

```
 ┌─────────────────┐
 │  Cron Scheduler │ (Disparo programado vía CRON_SCHEDULE)
 └────────┬────────┘
          │
          ▼
 ┌───────────────────────────────────────────────────────────┐
 │               Docker Container (adguard-reports)          │
 │                                                           │
 │  entrypoint.sh ──► main.py (Orquestador)                  │
 │                         │                                 │
 │        ┌────────────────┼────────────────┐                │
 │        ▼                ▼                ▼                │
 │  adguard_client   data_analyzer    report_generator       │
 │   (API REST)       + classifier   (ReportLab+Matplotlib)  │
 │        │                │                │                │
 └────────┼────────────────┼────────────────┼────────────────┘
          │ (GET logs)     │                │ (PDFs)
          ▼                │                ▼
 ┌─────────────────┐       │       ┌─────────────────┐
 │  AdGuard Home   │       │       │  ./reports/     │ (Volumen local)
 │  (API homelab)  │       │       └────────┬────────┘
 └─────────────────┘       │                │
                           ▼                ▼
                 ┌────────────────────────────────┐
                 │    email_sender.py (Resend)    │
                 └───────────────┬────────────────┘
                                 │ (POST /emails con PDFs)
                                 ▼
                     ┌───────────────────────┐
                     │   Resend API / Email  │
                     └───────────────────────┘
```

> 💡 *Puedes abrir el archivo interactivo [`architecture.html`](architecture.html) en tu navegador para explorar el diagrama completo en temas claro/oscuro.*

### Flujo de ejecución:
1. **Disparo:** El servicio de cron dentro del contenedor despierta a la hora configurada (o inmediatamente si `RUN_ON_START=true`).
2. **Extracción:** Se conecta a la API REST de AdGuard Home (`/control/clients` y `/control/querylog`), paginando todos los registros de las últimas 24 horas.
3. **Análisis:** Filtra los registros por cliente (IPs y Client IDs) y calcula estadísticas de bloqueo, horas pico, categorías de sitios y score de riesgo.
4. **Renderizado:** Genera informes PDF con diseño profesional, tablas formateadas y gráficos vectoriales generados con Matplotlib.
5. **Persistencia y Envío:** Guarda los archivos en el volumen `./reports/YYYY-MM-DD/` y los envía por correo electrónico usando la API de Resend.

---

## 🚀 Despliegue Rápido (Recomendado)

### 1. Clonar el repositorio
```bash
git clone https://github.com/kevin10191992/adguardhomeReports.git
cd adguardhomeReports
```

### 2. Configurar variables de entorno
Copia la plantilla `.env.example` y edita tus credenciales:
```bash
cp .env.example .env
```

Edita `.env` con tus datos:
```env
# AdGuard Home
ADGUARD_URL=http://192.168.1.1:3000
ADGUARD_USER=admin
ADGUARD_PASS=tu_password_seguro

# Resend Email
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx
EMAIL_FROM=AdGuard Reports <onboarding@resend.dev> # o tu dominio verificado
EMAIL_TO=tu_correo@gmail.com

# Programación (Cron) y Zona Horaria
CRON_SCHEDULE=0 6 * * *
TZ=America/Bogota

# Ejecutar inmediatamente al encender el contenedor
RUN_ON_START=true
```

### 3. Iniciar con Docker Compose
La imagen ya se compila y publica automáticamente en **GitHub Container Registry (GHCR)** para `amd64` y `arm64`:

```bash
# Descargar la imagen e iniciar en segundo plano
docker compose up -d

# Ver los logs en tiempo real
docker compose logs -f adguard-reports
```

---

## ⚙️ Variables de Entorno Disponibles

| Variable | Requerida | Por Defecto | Descripción |
|---|:---:|:---:|---|
| `ADGUARD_URL` | Sí | - | URL base de tu AdGuard Home (ej. `http://192.168.1.100:3000`) |
| `ADGUARD_USER` | Sí | - | Usuario administrador de AdGuard Home |
| `ADGUARD_PASS` | Sí | - | Contraseña de AdGuard Home |
| `RESEND_API_KEY` | Sí | - | API Key de [Resend](https://resend.com) (`re_...`) |
| `EMAIL_FROM` | Sí | - | Remitente del correo (ej. `reportes@tudominio.com` o `onboarding@resend.dev`) |
| `EMAIL_TO` | Sí | - | Destinatario(s). Separar múltiples con comas: `user1@mail.com,user2@mail.com` |
| `CRON_SCHEDULE` | No | `0 6 * * *` | Expresión cron para el job diario (por defecto: 6:00 AM) |
| `TZ` | No | `America/Bogota` | Zona horaria del contenedor para cron y fechas de informes |
| `RUN_ON_START` | No | `true` | Si es `true`, genera un informe inmediatamente al arrancar el contenedor |
| `QUERYLOG_HOURS` | No | `24` | Ventana de horas hacia atrás a consultar en el querylog |
| `QUERYLOG_LIMIT` | No | `5000` | Límite máximo de consultas a traer por cliente |
| `TOP_DOMAINS_COUNT` | No | `20` | Número de dominios top a incluir en tablas y gráficos |
| `REPORTS_DIR` | No | `/app/reports` | Ruta dentro del contenedor donde se guardan los PDFs |
| `LOG_LEVEL` | No | `INFO` | Nivel de logs (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

---

## 📄 Contenido del Informe PDF

Cada cliente recibe un documento PDF de diseño limpio y corporativo que incluye:

1. **Portada Ejecutiva:** Datos del cliente, IPs asignadas, fecha y período evaluado.
2. **Resumen Numérico:** Total de consultas, consultas permitidas vs bloqueadas, porcentaje de bloqueo y promedio por hora.
3. **Gráfico de Actividad por Hora:** Gráfico de barras de 24 horas (total vs bloqueado) indicando la hora pico.
4. **Top Dominios Más Consultados:** Gráfico circular (Pie Chart) y tabla con los dominios más frecuentes.
5. **Top Dominios Bloqueados:** Detalle de sitios bloqueados y la razón del filtro (Lista negra, Servicio bloqueado, etc.).
6. **Clasificación por Categorías:** Gráfico y tabla porcentual del tipo de tráfico (Streaming, Redes, Juegos, etc.).
7. **Tipos de Consulta DNS:** Distribución de registros consultados (A, AAAA, HTTPS, TXT...).
8. **Seguridad y Amenazas:** Semáforo de riesgo (Bajo/Medio/Alto) desglosado por Malware, Phishing, Control Parental y Rastreadores.
9. **Rendimiento:** Tiempos de respuesta DNS promedio, mínimo, máximo y servidores upstream utilizados.

---

## 🛠️ Ejecución Local sin Docker (Desarrollo)

Si prefieres ejecutar el script directamente con Python en tu máquina:

```bash
# 1. Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno (.env)
cp .env.example .env
# Edita las variables en .env

# 4. Ejecutar el orquestador
python main.py
```

Los PDFs generados se encontrarán en la carpeta `./reports/YYYY-MM-DD/`.

---

## 📦 CI/CD Automatizado

El repositorio cuenta con un flujo de **GitHub Actions** ([`.github/workflows/docker-publish.yml`](.github/workflows/docker-publish.yml)) que:
- Compila automáticamente la imagen Docker en cada `push` a la rama `main` o al crear etiquetas de versión (`v*.*.*`).
- Publica la imagen lista para usar en **GitHub Container Registry**:
  ```bash
  docker pull ghcr.io/kevin10191992/adguardhomereports:latest
  ```
- Soporta arquitecturas cruzadas mediante Docker Buildx: `linux/amd64` y `linux/arm64`.

---

## 🤝 Contribuciones y Licencia

Las contribuciones, sugerencias y mejoras son bienvenidas. Si encuentras algún problema o tienes una idea para una nueva categoría o gráfico, abre un *Issue* o envía un *Pull Request*.

Distribuido bajo la licencia **MIT**.
