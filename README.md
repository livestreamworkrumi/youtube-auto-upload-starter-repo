# YouTube Auto Upload Starter

A production-ready pipeline for automatically downloading videos from Instagram accounts, transforming them into YouTube Shorts format, and uploading them to YouTube with admin approval workflow via Telegram.

## Features

- **Instagram Integration**: Download videos from public Instagram accounts using instaloader
- **Video Transformation**: Convert to 9:16 vertical format (1080x1920) with intro/outro and overlays
- **Deduplication**: Prevent duplicates using Instagram post ID and perceptual hashing (pHash)
- **Scheduled Publishing**: Automatically publish 3 videos per day at configured times (Pakistan timezone)
- **Admin Approval**: Telegram-based approval workflow before YouTube upload
- **YouTube Integration**: Resumable uploads with proper OAuth authentication
- **Permission Tracking**: Store permission proof artifacts for each video
- **Demo Mode**: Fully functional offline mode for testing and development

## Quick Start in GitHub Codespaces

1. **Open in Codespaces**: Click the "Code" button and select "Open in Codespaces"
2. **Install Dependencies**: The devcontainer will automatically install all dependencies including FFmpeg
3. **Run Demo Mode**: 
   ```bash
   make run-demo
   ```
4. **Test the Pipeline**: The demo mode will process sample videos through the entire pipeline

## Development Setup

### Prerequisites

- Python 3.11+
- FFmpeg (included in devcontainer)
- Telegram Bot Token (for real mode)
- YouTube API credentials (for real mode)

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd youtube-auto-upload-starter-repo

# Install dependencies
make install

# Or manually:
pip install -r requirements.txt
```

### Demo Mode (No External APIs Required)

Demo mode uses sample videos and mocked external services:

```bash
# Set demo mode
export DEMO_MODE=true

# Run the application
make run-demo

# Or manually:
python -m app.main
```

The demo will:
1. Process sample videos from `sample_videos/`
2. Transform them to YouTube Shorts format
3. Send preview to Telegram (mocked)
4. Simulate approval and upload process
5. Store results in local SQLite database

### Real Mode Setup

1. **Create Telegram Bot**:
   - Message @BotFather on Telegram
   - Create a new bot and get the token
   - Get your admin user ID

2. **YouTube API Setup**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing
   - Enable YouTube Data API v3
   - Create OAuth 2.0 credentials (Desktop application)
   - Download `client_secrets.json`

3. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Run OAuth Flow**:
   ```bash
   python scripts/run_oauth_flow.py
   ```

5. **Start Real Mode**:
   ```bash
   export DEMO_MODE=false
   make run
   ```

## Configuration

Key environment variables (see `.env.example` for full list):

- `DEMO_MODE`: Enable demo mode (true/false)
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `TELEGRAM_ADMIN_ID`: Your Telegram user ID
- `TIMEZONE`: Timezone for scheduling (default: Asia/Karachi)
- `SCHEDULE_TIMES`: Comma-separated times (default: 08:00,12:00,16:00)
- `YOUTUBE_CLIENT_SECRETS`: Path to client_secrets.json
- `TOKEN_FILE`: Path to store OAuth token

## Usage

### Telegram Bot Commands

- `/start` - Start the scheduler
- `/stop` - Stop the scheduler
- `/status` - Show queue status and next run times
- `/add_target <username>` - Add Instagram username to monitor
- `/remove_target <username>` - Remove Instagram username
- `/list_targets` - List all monitored accounts

### Approval Workflow

1. System downloads and transforms videos
2. Sends preview to admin via Telegram with:
   - Transformed video/thumbnail
   - Suggested title, tags, and description
   - Original Instagram link
   - Permission proof path
3. Admin clicks "Approve" or "Reject"
4. Approved videos are uploaded to YouTube
5. Rejected videos are marked and skipped

## Testing

```bash
# Run all tests
make test

# Run specific test files
pytest tests/test_transform.py
pytest tests/test_dedupe.py
pytest tests/test_youtube_dryrun.py
```

## Project Structure

```
youtube-auto-upload-starter-repo/
├── app/                    # Main application code
│   ├── main.py            # FastAPI app and orchestration
│   ├── config.py          # Configuration management
│   ├── db.py              # Database setup
│   ├── models.py          # SQLAlchemy models
│   ├── ig_downloader.py   # Instagram downloader
│   ├── transform.py       # Video transformation
│   ├── dedupe.py          # Deduplication logic
│   ├── youtube_client.py  # YouTube upload client
│   ├── telegram_bot.py    # Telegram bot
│   ├── scheduler.py       # Job scheduling
│   ├── workers.py         # Background workers
│   └── utils.py           # Utility functions
├── assets/                # Branded intro/outro videos
├── sample_videos/         # Demo videos for testing
├── sample_proofs/         # Sample permission proofs
├── storage/               # Media storage (gitignored)
├── data/                  # SQLite database (gitignored)
├── tests/                 # Test suite
├── scripts/               # Utility scripts
└── migrations/            # Database migrations
```

## Database Schema

The application uses SQLite with the following main tables:

- `instagram_targets`: Monitored Instagram accounts
- `downloads`: Downloaded Instagram posts
- `transforms`: Video transformation records
- `uploads`: YouTube upload records
- `permissions`: Permission proof artifacts
- `logs`: Application logs

## API Endpoints

The FastAPI application provides these endpoints:

- `GET /health` - Health check
- `GET /status` - System status
- `POST /admin/approve/{upload_id}` - Approve upload (internal)
- `POST /admin/reject/{upload_id}` - Reject upload (internal)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Manual Setup Steps for Real Mode

1. **Obtain YouTube API Credentials**:
   - Go to Google Cloud Console
   - Create/select project
   - Enable YouTube Data API v3
   - Create OAuth 2.0 Desktop credentials
   - Download as `client_secrets.json`

2. **Set up Telegram Bot**:
   - Message @BotFather
   - Create bot and get token
   - Get your user ID from @userinfobot

3. **Configure Environment**:
   - Copy `.env.example` to `.env`
   - Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ADMIN_ID`
   - Set `DEMO_MODE=false`

4. **Run OAuth Flow**:
   ```bash
   python scripts/run_oauth_flow.py
   ```

5. **Start the Application**:
   ```bash
   make run
   ```

## Troubleshooting

- **FFmpeg not found**: Ensure FFmpeg is installed (included in devcontainer)
- **OAuth errors**: Delete `token.json` and re-run OAuth flow
- **Telegram bot not responding**: Check bot token and admin ID
- **YouTube upload fails**: Verify API quotas and credentials

For more help, check the logs in the database or file system.
