# Storage Directory

This directory stores all downloaded and processed media files.

## Structure

```
storage/
├── downloads/          # Downloaded Instagram videos
├── transforms/         # Transformed YouTube Shorts
├── thumbnails/         # Generated thumbnails
├── proofs/            # Permission proof files
└── temp/              # Temporary processing files
```

## Contents

### downloads/
- Raw videos downloaded from Instagram
- Named format: `{username}_{post_id}.mp4`
- Original quality and format from Instagram

### transforms/
- Videos transformed to YouTube Shorts format (9:16, 1080x1920)
- Named format: `transform_{id}_{post_id}.mp4`
- Includes intro/outro and overlays

### thumbnails/
- Thumbnail images for video previews
- Named format: `thumb_{id}_{post_id}.jpg`
- Used for Telegram previews and YouTube thumbnails

### proofs/
- Permission proof files
- Named format: `{username}_{post_id}_proof.txt`
- Document permission for content usage

### temp/
- Temporary files during processing
- Automatically cleaned up after processing

## File Management

- Files are automatically organized by the application
- Old files can be manually cleaned up if needed
- Database tracks all file paths and metadata
- Files are referenced by database records, not directly

## Backup Considerations

- This directory contains all processed content
- Consider backing up for disaster recovery
- Database records are essential for file management
- Test restore procedures with sample data

## Security

- Files are stored locally on the server
- Access is controlled by the application
- No direct web access to files
- Files served through application endpoints when needed

## Cleanup

To clean up old files:

1. Check database for file references
2. Remove unused files manually
3. Use application cleanup utilities if available
4. Monitor disk space usage

## Demo Mode

In demo mode, this directory may contain:
- Sample videos copied from `sample_videos/`
- Generated transform outputs
- Demo permission proofs
- Test thumbnails

## Production Mode

In production mode, this directory contains:
- Actual Instagram downloads
- Real transformed videos
- Actual permission proofs
- Production thumbnails

## Monitoring

Monitor this directory for:
- Disk space usage
- File count growth
- Processing errors
- Access patterns

## Troubleshooting

Common issues:
- **Disk full**: Clean up old files or increase storage
- **Permission errors**: Check file system permissions
- **Missing files**: Check database for orphaned records
- **Corrupted files**: Re-download or re-process affected content
