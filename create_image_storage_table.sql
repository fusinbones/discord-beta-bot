-- Create stored_images table for permanent image storage
-- This prevents Discord attachment URL expiration issues

CREATE TABLE IF NOT EXISTS stored_images (
    id BIGSERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    base64_data TEXT NOT NULL,
    content_type VARCHAR(100) NOT NULL DEFAULT 'image/png',
    file_size INTEGER NOT NULL,
    ambassador_id VARCHAR(50) NOT NULL,
    submission_id VARCHAR(50),
    original_discord_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed TIMESTAMPTZ,
    access_count INTEGER DEFAULT 0,
    
    -- Indexes for performance
    INDEX idx_stored_images_ambassador_id (ambassador_id),
    INDEX idx_stored_images_submission_id (submission_id),
    INDEX idx_stored_images_created_at (created_at)
);

-- Add RLS (Row Level Security) policies if needed
ALTER TABLE stored_images ENABLE ROW LEVEL SECURITY;

-- Policy to allow service role to manage all images
CREATE POLICY "Service role can manage stored_images" ON stored_images
    FOR ALL USING (auth.role() = 'service_role');

-- Policy to allow authenticated users to read images
CREATE POLICY "Authenticated users can read stored_images" ON stored_images
    FOR SELECT USING (auth.role() = 'authenticated');
