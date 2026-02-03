-- Create user if it doesn't exist
DO
$$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'grounded') THEN
      CREATE USER grounded WITH PASSWORD 'changeme';
   END IF;
END
$$;

-- Create database if it doesn't exist
SELECT 'CREATE DATABASE grounded OWNER grounded'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'grounded')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE grounded TO grounded;

-- Connect to the database and create extension
\c grounded

-- Create pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Grant schema permissions
GRANT ALL ON SCHEMA public TO grounded;
