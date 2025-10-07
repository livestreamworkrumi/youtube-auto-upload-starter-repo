#!/usr/bin/env python3
"""
Interactive OAuth flow script for YouTube API authentication.

This script helps set up YouTube API authentication by running the OAuth flow
and saving the credentials to token.json for use by the application.
"""

import json
import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# YouTube API scopes
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']


def run_oauth_flow():
    """Run the OAuth flow for YouTube API authentication."""
    
    # Check for client secrets file
    client_secrets_path = Path("client_secrets.json")
    if not client_secrets_path.exists():
        print("❌ Error: client_secrets.json not found!")
        print("\nTo get client_secrets.json:")
        print("1. Go to Google Cloud Console (https://console.cloud.google.com/)")
        print("2. Create a new project or select existing one")
        print("3. Enable YouTube Data API v3")
        print("4. Create OAuth 2.0 credentials (Desktop application)")
        print("5. Download the credentials as 'client_secrets.json'")
        print("6. Place the file in the project root directory")
        return False
    
    print("🔐 Starting YouTube API OAuth flow...")
    print(f"📁 Using client secrets: {client_secrets_path}")
    
    # Check for existing token
    token_path = Path("token.json")
    credentials = None
    
    if token_path.exists():
        print("🔄 Found existing token.json, refreshing if needed...")
        credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    
    # If there are no valid credentials, authenticate
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            print("🔄 Refreshing expired credentials...")
            credentials.refresh(Request())
        else:
            print("🚀 Starting OAuth flow...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secrets_path), SCOPES
            )
            
            print("\n📱 A browser window will open for authentication.")
            print("   Please log in with your YouTube account and authorize the application.")
            print("   ⚠️  Make sure you're logged into the correct YouTube channel!")
            
            # Run the OAuth flow
            credentials = flow.run_local_server(port=0)
        
        # Save credentials for next run
        with open(token_path, 'w') as token:
            token.write(credentials.to_json())
        
        print(f"✅ Credentials saved to {token_path}")
    
    # Test the credentials
    try:
        from googleapiclient.discovery import build
        
        youtube = build('youtube', 'v3', credentials=credentials)
        
        # Get channel information
        response = youtube.channels().list(part='snippet', mine=True).execute()
        
        if response['items']:
            channel = response['items'][0]
            channel_title = channel['snippet']['title']
            channel_id = channel['id']
            
            print(f"\n✅ Authentication successful!")
            print(f"📺 Channel: {channel_title}")
            print(f"🆔 Channel ID: {channel_id}")
            print(f"🔑 Token saved: {token_path}")
            
            return True
        else:
            print("❌ No YouTube channel found for this account")
            return False
            
    except Exception as e:
        print(f"❌ Error testing credentials: {e}")
        return False


def main():
    """Main function."""
    print("🎬 YouTube Auto Upload - OAuth Setup")
    print("=" * 40)
    
    try:
        success = run_oauth_flow()
        
        if success:
            print("\n🎉 OAuth setup completed successfully!")
            print("\nNext steps:")
            print("1. Set DEMO_MODE=false in your .env file")
            print("2. Configure your Telegram bot token and admin ID")
            print("3. Start the application with: python -m app.main")
        else:
            print("\n❌ OAuth setup failed!")
            print("Please check the error messages above and try again.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  OAuth flow cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
