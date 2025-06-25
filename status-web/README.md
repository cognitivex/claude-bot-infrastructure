# Claude Bot Status Web Dashboard

A self-hosted Flask web application for monitoring multiple Claude bot instances with Cloudflare tunnel support.

## 🚀 Quick Start

### 1. Start the Status Dashboard

```bash
# Start the status web service
docker-compose up status-web -d

# View logs
docker-compose logs -f status-web

# Check health
curl http://localhost:8080/api/health
```

### 2. Access Dashboard

- **Local Access**: http://localhost:8080
- **API Endpoint**: http://localhost:8080/api/status
- **Health Check**: http://localhost:8080/api/health

### 3. Configure Bots

The bots are already configured to report to the status web service via:
- `STATUS_WEB_URL=http://claude-status-web:5000` (Docker internal network)

## 🌐 Cloudflare Tunnel Setup

### 1. Install Cloudflared

```bash
# macOS
brew install cloudflared

# Windows
winget install --id Cloudflare.cloudflared

# Linux
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```

### 2. Authenticate with Cloudflare

```bash
cloudflared tunnel login
```

### 3. Create Tunnel

```bash
# Create a new tunnel
cloudflared tunnel create claude-bot-status

# Note the tunnel UUID from output
```

### 4. Configure Tunnel

Edit `cloudflare-tunnel.yml`:

```yaml
tunnel: YOUR_TUNNEL_UUID_HERE
credentials-file: /home/user/.cloudflared/YOUR_TUNNEL_UUID_HERE.json

ingress:
  - hostname: status.yourdomain.com
    service: http://localhost:8080
  - service: http_status:404
```

### 5. Route DNS

```bash
# Route your domain to the tunnel
cloudflared tunnel route dns claude-bot-status status.yourdomain.com
```

### 6. Run Tunnel

```bash
# Run the tunnel
cloudflared tunnel --config ./cloudflare-tunnel.yml run claude-bot-status

# Or run as service (Linux/macOS)
sudo cloudflared service install --config ./cloudflare-tunnel.yml
```

## 📊 API Endpoints

### Get All Bot Status
```bash
GET /api/status
```

Response:
```json
{
  "statuses": [
    {
      "bot_id": "claude-bot-nodejs",
      "status": "running",
      "health": "healthy",
      "repository": "user/repo",
      "uptime": "2h 15m",
      "queued_tasks": 3,
      "processed_tasks": 12,
      "timestamp": "2025-06-24T22:15:00Z"
    }
  ],
  "count": 1,
  "last_updated": "2025-06-24T22:16:00Z"
}
```

### Update Bot Status
```bash
POST /api/status/{bot_id}
Content-Type: application/json

{
  "status": "running",
  "health": "healthy",
  "queued_tasks": 5,
  "processed_tasks": 20,
  "uptime": "3h 30m"
}
```

### Get Specific Bot
```bash
GET /api/status/{bot_id}
```

### Health Check
```bash
GET /api/health
```

## 🔧 Configuration

### Environment Variables

```bash
# Flask configuration
FLASK_ENV=production
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=false

# Data storage
STATUS_DATA_DIR=/app/data

# Bot configuration  
STATUS_WEB_URL=http://claude-status-web:5000
```

### Docker Compose

The status web service is included in the main `docker-compose.yml`:

```yaml
status-web:
  build: ./status-web
  ports:
    - "8080:5000"
  volumes:
    - status-data:/app/data
  environment:
    - FLASK_ENV=production
```

## 🎨 Features

- **Real-time Dashboard**: Auto-refreshing every 30 seconds
- **RESTful API**: Easy integration with external tools
- **Health Monitoring**: Built-in health checks
- **Persistent Storage**: Bot status persisted to disk
- **Auto-cleanup**: Removes stale bot data after 1 hour
- **Responsive Design**: Mobile-friendly interface
- **Statistics Overview**: Total bots, active count, queue metrics

## 🔍 Monitoring

### Dashboard Features

- **Bot Status Cards**: Visual health indicators
- **Queue Metrics**: Pending and processed task counts
- **Recent Activity**: Latest bot actions and completions
- **Repository Links**: Quick access to target projects
- **Uptime Tracking**: How long each bot has been running
- **Error Display**: Shows any bot errors or issues

### Status Indicators

- 🟢 **Healthy/Running**: Bot is active and processing
- 🟡 **Idle**: Bot is running but no recent activity
- 🔴 **Unhealthy**: Bot has errors or issues
- ⚫ **Offline**: Bot hasn't reported in over 1 hour

## 🛠️ Troubleshooting

### Dashboard Not Loading

```bash
# Check if service is running
docker-compose ps status-web

# View logs
docker-compose logs status-web

# Test API directly
curl http://localhost:8080/api/health
```

### Bots Not Reporting

```bash
# Check bot logs
docker-compose logs claude-bot-dotnet

# Test status reporting manually
docker exec claude-bot-dotnet python3 /bot/scripts/status_reporter.py --bot-id test
```

### Cloudflare Tunnel Issues

```bash
# Check tunnel status
cloudflared tunnel info claude-bot-status

# Test tunnel connectivity
cloudflared tunnel run --url http://localhost:8080

# View tunnel logs
cloudflared tunnel --config ./cloudflare-tunnel.yml run claude-bot-status --loglevel debug
```

## 📱 Mobile Access

The dashboard is fully responsive and works on mobile devices. Access via your Cloudflare tunnel domain on any device.

## 🔐 Security

- **No External Dependencies**: Fully self-hosted
- **Internal Network**: Bots communicate via Docker network
- **Cloudflare Protection**: DDoS protection and caching
- **Health Checks**: Automated monitoring of service health

## 🚀 Production Deployment

### Docker Compose Production

```yaml
status-web:
  image: your-registry/claude-bot-status:latest
  ports:
    - "8080:5000"
  environment:
    - FLASK_ENV=production
  restart: unless-stopped
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:5000/api/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

### Cloudflare Tunnel as Service

```bash
# Install as system service
sudo cloudflared service install --config /path/to/cloudflare-tunnel.yml

# Start service
sudo systemctl start cloudflared
sudo systemctl enable cloudflared
```