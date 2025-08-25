# SDN-API

A FastAPI-based service that provides access to the Specially Designated Nationals (SDN) sanctions list for Aurelia Bank's Anti-Money Laundering (AML) operations.

## Overview

Aurelia Bank maintains a database of at-risk individuals and entities to identify and prevent fraudulent transactions. This API provides access to the comprehensive SDN list from [OpenSanctions](https://data.opensanctions.org/datasets/20250806/us_ofac_sdn/targets.simple.csv), which contains information about individuals and entities subject to OFAC sanctions.

**⚠️ Important**: Some of these individuals could be customers of the bank, making this data critical for preventing money laundering activities.

## Features

- **Real-time SDN Lookup**: Search the sanctions list by name with case-insensitive matching
- **Caching**: Built-in caching mechanism to reduce external API calls
- **Health Monitoring**: Health check endpoint for service monitoring
- **RESTful API**: Clean, documented API endpoints
- **CORS Support**: Cross-origin resource sharing enabled for web applications

## API Endpoints

### Health Check
```
GET /healthz
```
Returns service status and metadata about the SDN data source.

**Response:**
```json
{
  "status": "ok",
  "rows": 12345,
  "source": "https://data.opensanctions.org/datasets/20250806/us_ofac_sdn/targets.simple.csv"
}
```

### SDN Lookup
```
GET /getsdn?name={search_term}
```
Search for SDNs by name (minimum 2 characters).

**Parameters:**
- `name` (required): Search term for SDN names (case-insensitive contains match)

**Response:**
```json
{
  "count": 5,
  "results": [
    {
      "id": "12345",
      "name": "John Doe",
      "birth_date": "1980-01-01",
      "countries": "US,UK",
      "addresses": "123 Main St, New York, NY",
      "sanctions": "OFAC SDN",
      "dataset": "us_ofac_sdn"
    }
  ]
}
```

## Data Schema

The API returns SDN data with the following fields:
- `id`: Unique identifier
- `name`: Full name of the sanctioned individual/entity
- `birth_date`: Date of birth (if available)
- `countries`: Comma-separated list of associated countries
- `addresses`: Known addresses
- `sanctions`: Type of sanctions applied
- `dataset`: Source dataset identifier

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SDN_CSV_URL` | OpenSanctions SDN URL | Source URL for SDN data |
| `SDN_CACHE_TTL` | 3600 | Cache TTL in seconds |
| `SDN_RESULT_LIMIT` | 200 | Maximum results returned per query |

## Local Development

### Prerequisites
- Python 3.11+
- pip

### Setup
1. Clone the repository:
```bash
git clone <repository-url>
cd sdn-api
```

2. Create a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the development server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### API Documentation
Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Docker Deployment

### Build Image
```bash
docker build -f deploy/Dockerfile -t sdn-api .
```

### Run Container
```bash
docker run -p 8000:8000 sdn-api
```

## Production Deployment (GCP VM)

### Systemd Service Setup

1. Create the service file `/etc/systemd/system/sdn-api.service`:
```ini
[Unit]
Wants=network-online.target
After=network-online.target nss-user-lookup.target systemd-user-sessions.service

[Service]
User=lara_yasser_kotb
Group=lara_yasser_kotb
WorkingDirectory=/home/lara_yasser_kotb/sdn-api
Environment=PATH=/home/lara_yasser_kotb/sdn-api/.venv/bin
ExecStart=
ExecStart=/home/lara_yasser_kotb/sdn-api/.venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3
```

2. Reload and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl restart sdn-api
sudo systemctl status sdn-api --no-pager
```

3. View logs:
```bash
journalctl -u sdn-api -n 100 -xe --no-pager
```

### GCP Firewall Configuration

1. Authenticate with Google Cloud:
```bash
gcloud auth login
gcloud auth list
gcloud config set project aurelia-470113
```

2. Create firewall rule for port 8000:
```bash
gcloud compute firewall-rules create allow-sdn-api-8000 \
  --network=default \
  --direction=INGRESS \
  --action=ALLOW \
  --priority=1000 \
  --rules=tcp:8000 \
  --source-ranges=0.0.0.0/0 \
  --target-tags=sdn-api
```

3. Tag your VM instance:
```bash
gcloud compute instances add-tags aurelia-sdn-api-vm \
  --zone=us-central1-b \
  --tags=sdn-api
```

4. Verify configuration:
```bash
gcloud compute instances describe aurelia-sdn-api-vm \
  --zone=us-central1-b \
  --format='table(name,networkInterfaces[0].network,tags.items)'

gcloud compute firewall-rules list \
  --filter='name=allow-sdn-api-8000' \
  --format='table(name,network,direction,priority,sourceRanges,allowed,targetTags,disabled)'
```

## Usage Examples

### Python Client
```python
import httpx

async def search_sdn(name):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://your-api-host:8000/getsdn?name={name}")
        return response.json()

# Usage
results = await search_sdn("John")
```

### cURL
```bash
# Health check
curl http://your-api-host:8000/healthz

# Search for SDNs
curl "http://your-api-host:8000/getsdn?name=John"
```

### JavaScript/Node.js
```javascript
const response = await fetch('http://your-api-host:8000/getsdn?name=John');
const data = await response.json();
console.log(`Found ${data.count} SDNs`);
```

## Security Considerations

- The API is configured to accept connections from any origin (CORS enabled)
- Consider implementing authentication/authorization for production use
- Monitor API usage and implement rate limiting if needed
- Ensure the VM instance is properly secured with appropriate firewall rules

## Monitoring and Maintenance

- Use the `/healthz` endpoint for health checks and monitoring
- Monitor systemd service status: `sudo systemctl status sdn-api`
- Check logs: `journalctl -u sdn-api -f`
- The service automatically restarts on failure (Restart=always)

## Troubleshooting

### Common Issues

1. **Service won't start**: Check logs with `journalctl -u sdn-api -n 50`
2. **Port 8000 not accessible**: Verify firewall rules and VM tags
3. **CSV fetch failures**: Check network connectivity and source URL availability

### Debug Commands
```bash
# Check service status
sudo systemctl status sdn-api

# View recent logs
journalctl -u sdn-api -n 100 -xe --no-pager

# Test API locally
curl http://localhost:8000/healthz

# Check port binding
netstat -tlnp | grep 8000
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions related to this API, please contact the Aurelia Bank development team.
