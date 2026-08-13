-- RAG Pipeline Database Schema
-- This creates the necessary tables for the RAG pipeline
--
-- Voraussetzung: 01_shared_functions.sql (public.update_updated_at_column()).

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Documents table - stores metadata about processed documents
CREATE TABLE IF NOT EXISTS documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  source_type TEXT NOT NULL CHECK (source_type IN ('pdf', 'web', 'upload', 'api')),
  source_url TEXT,
  file_path TEXT,
  content_hash TEXT UNIQUE,
  content_length INTEGER,
  chunk_count INTEGER DEFAULT 0,
  metadata JSONB DEFAULT '{}',
  processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
  neo4j_document_id TEXT, -- Reference to Neo4j document node
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Document chunks table - stores individual text chunks
CREATE TABLE IF NOT EXISTS document_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
  chunk_index INTEGER NOT NULL,
  content TEXT NOT NULL,
  content_length INTEGER,
  start_position INTEGER,
  end_position INTEGER,
  neo4j_node_id TEXT, -- Reference to Neo4j vector node
  embedding_model TEXT DEFAULT 'llama3.2:latest',
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RAG sessions table - stores query sessions and responses
CREATE TABLE IF NOT EXISTS rag_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID, -- Can be linked to auth.users if needed
  session_name TEXT,
  query TEXT NOT NULL,
  query_embedding_model TEXT DEFAULT 'llama3.2:latest',
  response TEXT,
  response_model TEXT DEFAULT 'llama3.2:latest',
  context_documents UUID[], -- Array of document IDs used for context
  context_chunks UUID[], -- Array of chunk IDs used for context
  similarity_threshold FLOAT DEFAULT 0.7,
  max_context_chunks INTEGER DEFAULT 5,
  processing_time_ms INTEGER,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Vector search logs - for monitoring and optimization
CREATE TABLE IF NOT EXISTS vector_search_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES rag_sessions(id),
  query_text TEXT NOT NULL,
  search_type TEXT DEFAULT 'similarity', -- 'similarity', 'hybrid', 'keyword'
  results_count INTEGER,
  search_time_ms INTEGER,
  similarity_scores FLOAT[],
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Processing jobs table - for tracking background processing
CREATE TABLE IF NOT EXISTS processing_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_type TEXT NOT NULL CHECK (job_type IN ('pdf_processing', 'web_scraping', 'embedding_generation', 'vector_indexing')),
  status TEXT DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'completed', 'failed')),
  input_data JSONB NOT NULL,
  output_data JSONB DEFAULT '{}',
  error_message TEXT,
  started_at TIMESTAMP WITH TIME ZONE,
  completed_at TIMESTAMP WITH TIME ZONE,
  processing_time_ms INTEGER,
  retry_count INTEGER DEFAULT 0,
  max_retries INTEGER DEFAULT 3,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_documents_source_type ON documents(source_type);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(processing_status);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);
CREATE INDEX IF NOT EXISTS idx_documents_content_hash ON documents(content_hash);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_chunk_index ON document_chunks(document_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_chunks_neo4j_node_id ON document_chunks(neo4j_node_id);

CREATE INDEX IF NOT EXISTS idx_rag_sessions_user_id ON rag_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_rag_sessions_created_at ON rag_sessions(created_at);

CREATE INDEX IF NOT EXISTS idx_vector_search_logs_session_id ON vector_search_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_vector_search_logs_created_at ON vector_search_logs(created_at);

CREATE INDEX IF NOT EXISTS idx_processing_jobs_status ON processing_jobs(status);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_job_type ON processing_jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_created_at ON processing_jobs(created_at);

-- updated_at trigger (Funktion aus 01_shared_functions.sql)
CREATE OR REPLACE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- Create function to automatically update chunk_count in documents
CREATE OR REPLACE FUNCTION update_document_chunk_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE documents
        SET chunk_count = (
            SELECT COUNT(*)
            FROM document_chunks
            WHERE document_id = NEW.document_id
        )
        WHERE id = NEW.document_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE documents
        SET chunk_count = (
            SELECT COUNT(*)
            FROM document_chunks
            WHERE document_id = OLD.document_id
        )
        WHERE id = OLD.document_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ language 'plpgsql';

CREATE OR REPLACE TRIGGER update_chunk_count_on_insert
    AFTER INSERT ON document_chunks
    FOR EACH ROW
    EXECUTE FUNCTION update_document_chunk_count();

CREATE OR REPLACE TRIGGER update_chunk_count_on_delete
    AFTER DELETE ON document_chunks
    FOR EACH ROW
    EXECUTE FUNCTION update_document_chunk_count();

-- Create RLS policies (optional, for multi-tenant scenarios)
-- ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE rag_sessions ENABLE ROW LEVEL SECURITY;

-- Example RLS policy (uncomment if needed)
-- CREATE POLICY "Users can only see their own documents" ON documents
--     FOR ALL USING (auth.uid() = user_id);

-- Hinweis: Die frueheren Beispiel-/Demo-Datensaetze ("Example PDF Document",
-- "Example Web Page") wurden hier bewusst entfernt. Sie waren nicht wirklich
-- idempotent (content_hash blieb NULL, NULL <> NULL bei UNIQUE greift nicht,
-- ON CONFLICT (content_hash) DO NOTHING verhinderte daher keine Duplikate -
-- verifiziert: 2 Zeilen wurden bei jedem erneuten Lauf zu weiteren 2). Test-/
-- Demodaten gehoeren ohnehin nicht in eine Infrastruktur-Migration.

-- Create views for common queries
CREATE OR REPLACE VIEW document_summary AS
SELECT
    d.id,
    d.title,
    d.source_type,
    d.source_url,
    d.chunk_count,
    d.processing_status,
    d.created_at,
    COUNT(dc.id) as actual_chunk_count,
    AVG(dc.content_length) as avg_chunk_length
FROM documents d
LEFT JOIN document_chunks dc ON d.id = dc.document_id
GROUP BY d.id, d.title, d.source_type, d.source_url, d.chunk_count, d.processing_status, d.created_at;

CREATE OR REPLACE VIEW recent_rag_sessions AS
SELECT
    rs.id,
    rs.query,
    rs.response,
    rs.processing_time_ms,
    rs.created_at,
    array_length(rs.context_documents, 1) as context_doc_count,
    array_length(rs.context_chunks, 1) as context_chunk_count
FROM rag_sessions rs
ORDER BY rs.created_at DESC
LIMIT 100;

-- Grant permissions (adjust as needed)
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
-- GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;
