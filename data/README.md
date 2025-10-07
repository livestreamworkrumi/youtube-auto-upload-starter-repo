# Database Directory

This directory contains the SQLite database file for the application.

## Files

- `app.db` - Main SQLite database (created automatically)

## Database Schema

The database contains the following tables:

### Core Tables
- `instagram_targets` - Instagram accounts to monitor
- `downloads` - Downloaded Instagram posts
- `transforms` - Video transformation records
- `uploads` - YouTube upload records
- `approvals` - Admin approval workflow

### Metadata Tables
- `permissions` - Permission proof artifacts
- `logs` - Application logs
- `system_status` - System status and configuration

## Configuration

The database URL is configured via the `DB_URL` environment variable:
- Default: `sqlite:///./data/app.db`
- Can be changed to PostgreSQL, MySQL, etc.

## Backup

**Important**: Always backup the database before:
- System updates
- Configuration changes
- Manual database modifications

### Backup Commands

```bash
# Create backup
cp data/app.db data/app_backup_$(date +%Y%m%d_%H%M%S).db

# Restore from backup
cp data/app_backup_YYYYMMDD_HHMMSS.db data/app.db
```

## Migration

Database schema is managed by SQLAlchemy:
- Tables are created automatically on first run
- Schema changes require manual migration
- See `migrations/init.sql` for initial schema

## Monitoring

Monitor the database for:
- File size growth
- Query performance
- Connection issues
- Lock contention

## Demo Mode

In demo mode, the database contains:
- Sample Instagram targets
- Demo download records
- Test transform data
- Mock upload records

## Production Mode

In production mode, the database contains:
- Real Instagram targets
- Actual download records
- Production transform data
- Real upload records

## Troubleshooting

Common issues:

### Database Locked
```bash
# Check for running processes
ps aux | grep python
# Kill stuck processes
kill -9 <pid>
```

### Corrupted Database
```bash
# Check integrity
sqlite3 data/app.db "PRAGMA integrity_check;"
# Repair if needed
sqlite3 data/app.db ".recover" | sqlite3 data/app_recovered.db
```

### Permission Errors
```bash
# Fix permissions
chmod 664 data/app.db
chown $USER:$USER data/app.db
```

## Maintenance

Regular maintenance tasks:
- Vacuum database monthly
- Check for orphaned records
- Monitor disk usage
- Update statistics

```bash
# Vacuum database
sqlite3 data/app.db "VACUUM;"

# Analyze tables
sqlite3 data/app.db "ANALYZE;"
```

## Security

- Database file should have restricted permissions
- Regular backups are essential
- Consider encryption for sensitive data
- Monitor access logs
