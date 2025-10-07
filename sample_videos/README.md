# Sample Videos

This directory contains sample MP4 videos for demo mode testing.

## Files

- `sample1.mp4` - Sample video 1 (demo content)
- `sample2.mp4` - Sample video 2 (demo content)

## Usage

These videos are used when `DEMO_MODE=true` to simulate Instagram downloads
without requiring actual Instagram access. The videos should be small
(under 10MB each) and in MP4 format for testing the transformation pipeline.

## Creating Sample Videos

To create your own sample videos for testing:

1. Use any video editing software (e.g., OpenShot, DaVinci Resolve)
2. Create short videos (10-30 seconds) in any aspect ratio
3. Export as MP4 format
4. Keep file sizes small for quick testing
5. Place in this directory

## Note

In production mode, videos are downloaded from Instagram using the
instaloader library. These sample videos are only used for development
and testing purposes.
