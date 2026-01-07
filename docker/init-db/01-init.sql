-- KingSick Database Initialization Script
-- This script runs automatically when the PostgreSQL container is first created

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create indexes schema for better organization
-- (Tables will be created by Alembic migrations)

-- Grant permissions to default user
GRANT ALL PRIVILEGES ON DATABASE kingsick TO postgres;

-- Log initialization completion
DO $$
BEGIN
    RAISE NOTICE 'KingSick database initialized successfully';
END $$;
