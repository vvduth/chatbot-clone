# Digital Ocean App Platform Deployment

This directory contains the configuration for deploying the OptiBot scraper as a scheduled job on Digital Ocean App Platform.

## Setup Instructions

### 1. Prerequisites
- Digital Ocean account
- GitHub repository with this code
- Environment variables set up in Digital Ocean

### 2. Configure app.yaml

Before deploying, update the `app.yaml` file:

1. **Update GitHub repository**:
   ```yaml
   github:
     repo: vvduth/chatbot-clone
     branch: main
   ```

2. **Set environment variables** in Digital Ocean dashboard:
   - `OPENAI_API_KEY` (Secret)
   - `ZENDESK_API_TOKEN` (Secret)
   - `ZENDESK_EMAIL` (Secret) - Your Zendesk email address

### 3. Deploy via Digital Ocean CLI

```bash
# Install doctl if not already installed
# https://docs.digitalocean.com/reference/doctl/how-to/install/

# Authenticate
doctl auth init

# Create the app
doctl apps create --spec .do/app.yaml
```

### 4. Deploy via Digital Ocean Dashboard

1. Go to [Digital Ocean App Platform](https://cloud.digitalocean.com/apps)
2. Click "Create App"
3. Connect your GitHub repository
4. Select "Scheduled Job" as the app type
5. Configure:
   - **Schedule**: `0 0 * * *` (daily at midnight UTC)
   - **Dockerfile path**: `Dockerfile`
   - **Source directory**: `/`
6. Add environment variables (as secrets where applicable)
7. Add volume:
   - **Path**: `/app/data`
   - **Name**: `scraper-state`
   - **Size**: 1 GB
8. Deploy

## Schedule Configuration

The job runs daily at midnight UTC. To change the schedule, update the `cron` field in `app.yaml`:

```yaml
schedule:
  cron: "0 0 * * *"  # Daily at midnight UTC
```

Common cron patterns:
- `0 0 * * *` - Daily at midnight UTC
- `0 2 * * *` - Daily at 2 AM UTC
- `0 */6 * * *` - Every 6 hours
- `0 0 * * 0` - Weekly on Sunday at midnight

## Monitoring

- View logs in Digital Ocean dashboard under "Runtime Logs"
- Check job execution history in "Activity" tab
- Monitor resource usage in "Metrics" tab

## State Persistence

The state file (`data/state.json`) is persisted using a Digital Ocean volume mounted at `/app/data`. This ensures:
- State persists across container runs
- Delta detection works correctly
- Only changed articles are uploaded

## Troubleshooting

1. **Job not running**: Check schedule configuration and timezone
2. **State not persisting**: Verify volume is mounted correctly
3. **Authentication errors**: Check environment variables are set correctly
4. **API errors**: Check logs for detailed error messages
