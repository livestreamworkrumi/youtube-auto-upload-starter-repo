# Setup Guide

This guide will walk you through setting up the YouTube Auto Upload starter repository for both demo and production use.

## Quick Start (Demo Mode)

The fastest way to get started is with demo mode, which requires no external API credentials:

1. **Open in Codespaces**: Click the "Code" button and select "Open in Codespaces"
2. **Wait for setup**: The devcontainer will automatically install all dependencies
3. **Create demo data**: Run `make demo-db` to populate the database with sample data
4. **Start the app**: Run `make run-demo` to start in demo mode
5. **Test the API**: Visit `http://localhost:8000/docs` to see the API documentation

## Production Setup

For production use, you'll need to configure external APIs and credentials.

### 1. YouTube API Setup

1. **Go to Google Cloud Console**:
   - Visit [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one

2. **Enable YouTube Data API**:
   - Go to "APIs & Services" > "Library"
   - Search for "YouTube Data API v3"
   - Click "Enable"

3. **Create OAuth Credentials**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - Choose "Desktop application"
   - Download the credentials file as `client_secrets.json`
   - Place it in the project root directory

4. **Run OAuth Flow**:
   ```bash
   python scripts/run_oauth_flow.py
   ```
   - A browser window will open
   - Log in with your YouTube account
   - Authorize the application
   - The token will be saved to `token.json`

### 2. Telegram Bot Setup

1. **Create a Telegram Bot**:
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Send `/newbot` command
   - Follow the prompts to create your bot
   - Save the bot token

2. **Get Your User ID**:
   - Message [@userinfobot](https://t.me/userinfobot) on Telegram
   - Send any message to get your user ID

3. **Configure Environment**:
   - Copy `.env.example` to `.env`
   - Set `TELEGRAM_BOT_TOKEN` to your bot token
   - Set `TELEGRAM_ADMIN_ID` to your user ID

### 3. Environment Configuration

Create a `.env` file with your configuration:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# Production mode
DEMO_MODE=false

# Telegram configuration
TELEGRAM_BOT_TOKEN=your_actual_bot_token
TELEGRAM_ADMIN_ID=your_actual_user_id

# YouTube API
YOUTUBE_CLIENT_SECRETS=./client_secrets.json
TOKEN_FILE=./token.json

# Other settings
TIMEZONE=Asia/Karachi
SCHEDULE_TIMES=08:00,12:00,16:00
CHANNEL_TITLE=Your Channel Name
```

### 4. Start Production Mode

```bash
# Install dependencies
make install

# Start the application
make run
```

## Development Setup

For development and testing:

### 1. Local Development

```bash
# Clone the repository
git clone <your-repo-url>
cd youtube-auto-upload-starter-repo

# Install dependencies
make install

# Set up development environment
make setup-dev

# Run in demo mode
make run-demo
```

### 2. Running Tests

```bash
# Run all tests
make test

# Run tests with coverage
make test-coverage

# Run specific test files
pytest tests/test_transform.py -v
pytest tests/test_dedupe.py -v
pytest tests/test_youtube_dryrun.py -v
```

### 3. Code Quality

```bash
# Format code
make format

# Lint code
make lint

# Clean up generated files
make clean
```

## Docker Setup

### 1. Build Docker Image

```bash
docker build -t youtube-auto-upload .
```

### 2. Run with Docker

```bash
# Demo mode
docker run -p 8000:8000 -e DEMO_MODE=true youtube-auto-upload

# Production mode (with environment file)
docker run -p 8000:8000 --env-file .env youtube-auto-upload
```

### 3. Docker Compose (Optional)

Create a `docker-compose.yml` file:

```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEMO_MODE=true
    volumes:
      - ./storage:/workspaces/youtube-auto-upload-starter-repo/storage
      - ./data:/workspaces/youtube-auto-upload-starter-repo/data
```

Run with:
```bash
docker-compose up -d
```

## Troubleshooting

### Common Issues

1. **FFmpeg not found**:
   ```bash
   # Install FFmpeg
   sudo apt-get install ffmpeg
   ```

2. **Database connection errors**:
   ```bash
   # Check database file permissions
   chmod 664 data/app.db
   ```

3. **YouTube OAuth errors**:
   - Delete `token.json` and re-run OAuth flow
   - Check `client_secrets.json` is in the correct location

4. **Telegram bot not responding**:
   - Verify bot token is correct
   - Check admin ID is correct
   - Ensure bot is not blocked

5. **Permission errors**:
   ```bash
   # Fix file permissions
   chmod -R 755 storage/
   chmod -R 755 data/
   ```

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
make run-demo
```

### Health Checks

Check system status:

```bash
# API health check
curl http://localhost:8000/health

# System status
curl http://localhost:8000/status

# Statistics
curl http://localhost:8000/stats
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEMO_MODE` | `true` | Enable demo mode (no external APIs) |
| `TIMEZONE` | `Asia/Karachi` | Timezone for scheduling |
| `SCHEDULE_TIMES` | `08:00,12:00,16:00` | Upload schedule times |
| `TELEGRAM_BOT_TOKEN` | - | Telegram bot token |
| `TELEGRAM_ADMIN_ID` | - | Admin Telegram user ID |
| `YOUTUBE_CLIENT_SECRETS` | `./client_secrets.json` | YouTube API credentials |
| `TOKEN_FILE` | `./token.json` | OAuth token storage |
| `STORAGE_PATH` | `./storage` | Media storage directory |
| `DB_URL` | `sqlite:///./data/app.db` | Database connection |
| `LOG_LEVEL` | `INFO` | Logging level |

### Advanced Configuration

Edit `app/config.py` for advanced settings:

- `phash_threshold`: Duplicate detection sensitivity
- `max_retry_attempts`: Retry count for failed operations
- `chunk_size`: YouTube upload chunk size
- `download_timeout`: Instagram download timeout

## API Endpoints

The application provides these REST API endpoints:

- `GET /health` - Health check
- `GET /status` - System status
- `GET /stats` - Detailed statistics
- `POST /admin/run-pipeline` - Manual pipeline trigger
- `POST /admin/approve/{upload_id}` - Approve upload
- `POST /admin/reject/{upload_id}` - Reject upload

Access the interactive API documentation at `http://localhost:8000/docs`.

## Next Steps

After setup:

1. **Add Instagram targets** via Telegram bot commands
2. **Test the pipeline** with demo mode first
3. **Configure branded assets** (intro/outro videos)
4. **Set up monitoring** and logging
5. **Deploy to production** environment

## Support

For issues and questions:

1. Check the troubleshooting section above
2. Review the API documentation at `/docs`
3. Check the application logs
4. Create an issue in the repository

## Security Notes

- Never commit `client_secrets.json` or `token.json` to version control
- Use environment variables for sensitive configuration
- Regularly rotate API tokens and credentials
- Monitor API usage and quotas
- Implement proper backup strategies for the database
