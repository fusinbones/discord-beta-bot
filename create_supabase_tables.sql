-- Create ambassadors table
CREATE TABLE IF NOT EXISTS public.ambassadors (
    id BIGSERIAL PRIMARY KEY,
    discord_id TEXT UNIQUE NOT NULL,
    username TEXT NOT NULL,
    social_handles TEXT,
    platforms TEXT DEFAULT 'all',
    current_month_points INTEGER DEFAULT 0,
    total_points INTEGER DEFAULT 0,
    consecutive_months INTEGER DEFAULT 0,
    reward_tier TEXT DEFAULT 'none',
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create submissions table
CREATE TABLE IF NOT EXISTS public.submissions (
    id BIGSERIAL PRIMARY KEY,
    ambassador_id TEXT NOT NULL,
    platform TEXT,
    post_type TEXT,
    url TEXT,
    screenshot_hash TEXT,
    engagement_data JSONB,
    content_preview TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    points_awarded INTEGER DEFAULT 0,
    is_duplicate BOOLEAN DEFAULT FALSE,
    validity_status TEXT DEFAULT 'accepted',
    gemini_analysis JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (ambassador_id) REFERENCES ambassadors(discord_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_ambassadors_discord_id ON public.ambassadors(discord_id);
CREATE INDEX IF NOT EXISTS idx_ambassadors_status ON public.ambassadors(status);
CREATE INDEX IF NOT EXISTS idx_submissions_ambassador_id ON public.submissions(ambassador_id);
CREATE INDEX IF NOT EXISTS idx_submissions_timestamp ON public.submissions(timestamp);
CREATE INDEX IF NOT EXISTS idx_submissions_screenshot_hash ON public.submissions(screenshot_hash);

-- Enable Row Level Security (RLS)
ALTER TABLE public.ambassadors ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.submissions ENABLE ROW LEVEL SECURITY;

-- Create policies to allow service role access
CREATE POLICY "Allow service role full access on ambassadors" ON public.ambassadors
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Allow service role full access on submissions" ON public.submissions
    FOR ALL USING (auth.role() = 'service_role');

-- Grant permissions to service role
GRANT ALL ON public.ambassadors TO service_role;
GRANT ALL ON public.submissions TO service_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;
