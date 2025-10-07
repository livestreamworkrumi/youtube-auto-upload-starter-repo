-- Initial database schema for YouTube Auto Upload application
-- This file contains the SQL schema for all tables

-- Instagram targets table
CREATE TABLE IF NOT EXISTS instagram_targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(255) UNIQUE NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    last_checked DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_instagram_targets_username ON instagram_targets(username);

-- Downloads table
CREATE TABLE IF NOT EXISTS downloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_id INTEGER NOT NULL,
    ig_post_id VARCHAR(255) UNIQUE NOT NULL,
    ig_shortcode VARCHAR(255) NOT NULL,
    source_url TEXT NOT NULL,
    local_path VARCHAR(500) NOT NULL,
    permission_proof_path VARCHAR(500) NOT NULL,
    file_size INTEGER NOT NULL,
    duration_seconds INTEGER,
    caption TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (target_id) REFERENCES instagram_targets(id)
);

CREATE INDEX IF NOT EXISTS idx_downloads_ig_post_id ON downloads(ig_post_id);
CREATE INDEX IF NOT EXISTS idx_downloads_ig_shortcode ON downloads(ig_shortcode);
CREATE INDEX IF NOT EXISTS idx_downloads_target_id ON downloads(target_id);

-- Transforms table
CREATE TABLE IF NOT EXISTS transforms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    download_id INTEGER NOT NULL,
    input_path VARCHAR(500) NOT NULL,
    output_path VARCHAR(500) NOT NULL,
    thumbnail_path VARCHAR(500),
    phash VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    transform_duration_seconds INTEGER,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (download_id) REFERENCES downloads(id)
);

CREATE INDEX IF NOT EXISTS idx_transforms_phash ON transforms(phash);
CREATE INDEX IF NOT EXISTS idx_transforms_status ON transforms(status);
CREATE INDEX IF NOT EXISTS idx_transforms_download_id ON transforms(download_id);

-- Uploads table
CREATE TABLE IF NOT EXISTS uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transform_id INTEGER NOT NULL,
    yt_video_id VARCHAR(255),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    tags TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    uploaded_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transform_id) REFERENCES transforms(id)
);

CREATE INDEX IF NOT EXISTS idx_uploads_yt_video_id ON uploads(yt_video_id);
CREATE INDEX IF NOT EXISTS idx_uploads_status ON uploads(status);
CREATE INDEX IF NOT EXISTS idx_uploads_transform_id ON uploads(transform_id);

-- Approvals table
CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_id INTEGER NOT NULL,
    telegram_message_id INTEGER,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    approved_by VARCHAR(255),
    approved_at DATETIME,
    rejection_reason TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (upload_id) REFERENCES uploads(id)
);

CREATE INDEX IF NOT EXISTS idx_approvals_upload_id ON approvals(upload_id);
CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status);

-- Permissions table
CREATE TABLE IF NOT EXISTS permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    download_id INTEGER NOT NULL,
    proof_type VARCHAR(100) NOT NULL,
    proof_path VARCHAR(500) NOT NULL,
    proof_content BLOB,
    description TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (download_id) REFERENCES downloads(id)
);

CREATE INDEX IF NOT EXISTS idx_permissions_download_id ON permissions(download_id);

-- Logs table
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level VARCHAR(20) NOT NULL,
    module VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    details TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level);
CREATE INDEX IF NOT EXISTS idx_logs_created_at ON logs(created_at);

-- System status table
CREATE TABLE IF NOT EXISTS system_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scheduler_running BOOLEAN NOT NULL DEFAULT 0,
    last_run DATETIME,
    next_run DATETIME,
    total_downloads INTEGER NOT NULL DEFAULT 0,
    total_uploads INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    last_error_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Insert default system status record
INSERT OR IGNORE INTO system_status (id) VALUES (1);

-- Create triggers for updated_at timestamps
CREATE TRIGGER IF NOT EXISTS update_instagram_targets_updated_at 
    AFTER UPDATE ON instagram_targets
    BEGIN
        UPDATE instagram_targets SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_downloads_updated_at 
    AFTER UPDATE ON downloads
    BEGIN
        UPDATE downloads SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_transforms_updated_at 
    AFTER UPDATE ON transforms
    BEGIN
        UPDATE transforms SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_uploads_updated_at 
    AFTER UPDATE ON uploads
    BEGIN
        UPDATE uploads SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_approvals_updated_at 
    AFTER UPDATE ON approvals
    BEGIN
        UPDATE approvals SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_system_status_updated_at 
    AFTER UPDATE ON system_status
    BEGIN
        UPDATE system_status SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;
