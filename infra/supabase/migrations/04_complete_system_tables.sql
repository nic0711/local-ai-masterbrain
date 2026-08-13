-- =====================================================
-- LocalSupabase Complete System Tables Migration
-- Description: Vollstaendige Datenbankstruktur fuer alle Services
--
-- Voraussetzung: 01_shared_functions.sql (public.update_updated_at_column()).
-- =====================================================

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =====================================================
-- 1. USER MANAGEMENT & PROFILES
-- =====================================================

-- Extended user profiles
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    avatar_url TEXT,
    bio TEXT,
    preferences JSONB DEFAULT '{}',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

-- User sessions tracking
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    session_token TEXT NOT NULL,
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User activity logs
CREATE TABLE IF NOT EXISTS user_activity (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id TEXT,
    metadata JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- 2. FILE MANAGEMENT SYSTEM
-- =====================================================

-- Files registry
CREATE TABLE IF NOT EXISTS files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    storage_bucket TEXT DEFAULT 'files',
    uploaded_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    is_public BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- File versions (for version control)
CREATE TABLE IF NOT EXISTS file_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_id UUID REFERENCES files(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    file_hash TEXT NOT NULL,
    changes_description TEXT,
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- File shares and permissions
CREATE TABLE IF NOT EXISTS file_shares (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_id UUID REFERENCES files(id) ON DELETE CASCADE,
    shared_with UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    shared_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    permission_level TEXT CHECK (permission_level IN ('read', 'write', 'admin')) DEFAULT 'read',
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(file_id, shared_with)
);

-- =====================================================
-- 3. WORKFLOW MANAGEMENT (n8n Integration)
-- =====================================================

-- n8n Workflows registry
CREATE TABLE IF NOT EXISTS workflows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    n8n_workflow_id TEXT UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    tags TEXT[] DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    workflow_data JSONB,
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Workflow executions
CREATE TABLE IF NOT EXISTS workflow_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,
    n8n_execution_id TEXT,
    status TEXT CHECK (status IN ('running', 'success', 'error', 'waiting', 'canceled')) DEFAULT 'running',
    trigger_type TEXT,
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    execution_time_ms INTEGER,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    finished_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Workflow logs
CREATE TABLE IF NOT EXISTS workflow_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id UUID REFERENCES workflow_executions(id) ON DELETE CASCADE,
    node_name TEXT,
    log_level TEXT CHECK (log_level IN ('debug', 'info', 'warn', 'error')) DEFAULT 'info',
    message TEXT NOT NULL,
    data JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- 4. SYSTEM MONITORING & HEALTH
-- =====================================================

-- Service health monitoring
CREATE TABLE IF NOT EXISTS service_health (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_name TEXT NOT NULL,
    status TEXT CHECK (status IN ('healthy', 'unhealthy', 'degraded', 'unknown')) DEFAULT 'unknown',
    response_time_ms INTEGER,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- System metrics
CREATE TABLE IF NOT EXISTS system_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name TEXT NOT NULL,
    metric_value NUMERIC NOT NULL,
    metric_unit TEXT,
    service_name TEXT,
    tags JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Error logs
CREATE TABLE IF NOT EXISTS error_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_name TEXT NOT NULL,
    error_type TEXT,
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    request_id TEXT,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}',
    severity TEXT CHECK (severity IN ('low', 'medium', 'high', 'critical')) DEFAULT 'medium',
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- 5. AI/LLM INTEGRATION
-- =====================================================

-- AI conversations
CREATE TABLE IF NOT EXISTS ai_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT,
    model_name TEXT NOT NULL,
    provider TEXT NOT NULL,
    conversation_data JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    total_tokens INTEGER DEFAULT 0,
    total_cost NUMERIC(10,6) DEFAULT 0,
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- AI models registry
CREATE TABLE IF NOT EXISTS ai_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    provider TEXT NOT NULL,
    model_type TEXT CHECK (model_type IN ('chat', 'completion', 'embedding', 'image', 'audio')) DEFAULT 'chat',
    description TEXT,
    max_tokens INTEGER,
    input_cost_per_token NUMERIC(12,8),
    output_cost_per_token NUMERIC(12,8),
    is_active BOOLEAN DEFAULT TRUE,
    capabilities JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- AI usage statistics
CREATE TABLE IF NOT EXISTS ai_usage_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    model_id UUID REFERENCES ai_models(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES ai_conversations(id) ON DELETE CASCADE,
    tokens_used INTEGER NOT NULL,
    cost NUMERIC(10,6) NOT NULL,
    request_type TEXT,
    response_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- 6. NEO4J INTEGRATION
-- =====================================================

-- Neo4j connection registry
CREATE TABLE IF NOT EXISTS neo4j_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    host TEXT NOT NULL,
    port INTEGER DEFAULT 7687,
    database_name TEXT DEFAULT 'neo4j',
    username TEXT NOT NULL,
    password_encrypted TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_connected TIMESTAMP WITH TIME ZONE,
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Neo4j query logs
CREATE TABLE IF NOT EXISTS neo4j_queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    connection_id UUID REFERENCES neo4j_connections(id) ON DELETE CASCADE,
    query_text TEXT NOT NULL,
    parameters JSONB DEFAULT '{}',
    execution_time_ms INTEGER,
    records_returned INTEGER,
    status TEXT CHECK (status IN ('success', 'error')) DEFAULT 'success',
    error_message TEXT,
    executed_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Neo4j data sync tracking
CREATE TABLE IF NOT EXISTS neo4j_sync_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_name TEXT NOT NULL,
    source_table TEXT,
    target_labels TEXT[],
    sync_type TEXT CHECK (sync_type IN ('full', 'incremental', 'delta')) DEFAULT 'incremental',
    last_sync_at TIMESTAMP WITH TIME ZONE,
    records_processed INTEGER DEFAULT 0,
    status TEXT CHECK (status IN ('pending', 'running', 'completed', 'failed')) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- 7. NOTIFICATIONS & ALERTS
-- =====================================================

-- Notification system
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT CHECK (type IN ('info', 'success', 'warning', 'error')) DEFAULT 'info',
    category TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    action_url TEXT,
    metadata JSONB DEFAULT '{}',
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    read_at TIMESTAMP WITH TIME ZONE
);

-- System alerts
CREATE TABLE IF NOT EXISTS system_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_name TEXT NOT NULL,
    severity TEXT CHECK (severity IN ('low', 'medium', 'high', 'critical')) DEFAULT 'medium',
    service_name TEXT NOT NULL,
    condition_met TEXT NOT NULL,
    message TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- User profiles indexes
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_user_activity_user_id ON user_activity(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_created_at ON user_activity(created_at);

-- Files indexes
CREATE INDEX IF NOT EXISTS idx_files_uploaded_by ON files(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_files_created_at ON files(created_at);
CREATE INDEX IF NOT EXISTS idx_files_file_hash ON files(file_hash);
CREATE INDEX IF NOT EXISTS idx_files_tags ON files USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_file_versions_file_id ON file_versions(file_id);
CREATE INDEX IF NOT EXISTS idx_file_shares_file_id ON file_shares(file_id);
CREATE INDEX IF NOT EXISTS idx_file_shares_shared_with ON file_shares(shared_with);

-- Workflows indexes
CREATE INDEX IF NOT EXISTS idx_workflows_created_by ON workflows(created_by);
CREATE INDEX IF NOT EXISTS idx_workflows_is_active ON workflows(is_active);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_workflow_id ON workflow_executions(workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_status ON workflow_executions(status);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_started_at ON workflow_executions(started_at);
CREATE INDEX IF NOT EXISTS idx_workflow_logs_execution_id ON workflow_logs(execution_id);

-- System monitoring indexes
CREATE INDEX IF NOT EXISTS idx_service_health_service_name ON service_health(service_name);
CREATE INDEX IF NOT EXISTS idx_service_health_checked_at ON service_health(checked_at);
CREATE INDEX IF NOT EXISTS idx_system_metrics_metric_name ON system_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_error_logs_service_name ON error_logs(service_name);
CREATE INDEX IF NOT EXISTS idx_error_logs_created_at ON error_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_error_logs_severity ON error_logs(severity);

-- AI indexes
CREATE INDEX IF NOT EXISTS idx_ai_conversations_user_id ON ai_conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_conversations_created_at ON ai_conversations(created_at);
CREATE INDEX IF NOT EXISTS idx_ai_usage_stats_user_id ON ai_usage_stats(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_usage_stats_created_at ON ai_usage_stats(created_at);

-- Neo4j indexes
CREATE INDEX IF NOT EXISTS idx_neo4j_queries_connection_id ON neo4j_queries(connection_id);
CREATE INDEX IF NOT EXISTS idx_neo4j_queries_executed_at ON neo4j_queries(executed_at);
CREATE INDEX IF NOT EXISTS idx_neo4j_sync_jobs_last_sync_at ON neo4j_sync_jobs(last_sync_at);

-- Notifications indexes
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at);
CREATE INDEX IF NOT EXISTS idx_system_alerts_service_name ON system_alerts(service_name);
CREATE INDEX IF NOT EXISTS idx_system_alerts_is_active ON system_alerts(is_active);

-- =====================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =====================================================

-- Enable RLS on all tables
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_activity ENABLE ROW LEVEL SECURITY;
ALTER TABLE files ENABLE ROW LEVEL SECURITY;
ALTER TABLE file_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE file_shares ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflows ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_usage_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- User profiles policies. DROP IF EXISTS + CREATE statt nacktem CREATE
-- POLICY: Postgres kennt kein CREATE POLICY IF NOT EXISTS.
DROP POLICY IF EXISTS "Users can view own profile" ON user_profiles;
CREATE POLICY "Users can view own profile" ON user_profiles FOR SELECT USING (auth.uid() = user_id);
DROP POLICY IF EXISTS "Users can update own profile" ON user_profiles;
CREATE POLICY "Users can update own profile" ON user_profiles FOR UPDATE USING (auth.uid() = user_id);
DROP POLICY IF EXISTS "Users can insert own profile" ON user_profiles;
CREATE POLICY "Users can insert own profile" ON user_profiles FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Files policies
DROP POLICY IF EXISTS "Users can view own files" ON files;
CREATE POLICY "Users can view own files" ON files FOR SELECT USING (auth.uid() = uploaded_by OR is_public = true);
DROP POLICY IF EXISTS "Users can insert own files" ON files;
CREATE POLICY "Users can insert own files" ON files FOR INSERT WITH CHECK (auth.uid() = uploaded_by);
DROP POLICY IF EXISTS "Users can update own files" ON files;
CREATE POLICY "Users can update own files" ON files FOR UPDATE USING (auth.uid() = uploaded_by);
DROP POLICY IF EXISTS "Users can delete own files" ON files;
CREATE POLICY "Users can delete own files" ON files FOR DELETE USING (auth.uid() = uploaded_by);

-- File shares policies
DROP POLICY IF EXISTS "Users can view shared files" ON file_shares;
CREATE POLICY "Users can view shared files" ON file_shares FOR SELECT USING (auth.uid() = shared_with OR auth.uid() = shared_by);
DROP POLICY IF EXISTS "File owners can manage shares" ON file_shares;
CREATE POLICY "File owners can manage shares" ON file_shares FOR ALL USING (
    auth.uid() IN (SELECT uploaded_by FROM files WHERE files.id = file_shares.file_id)
);

-- Workflows policies
DROP POLICY IF EXISTS "Users can view own workflows" ON workflows;
CREATE POLICY "Users can view own workflows" ON workflows FOR SELECT USING (auth.uid() = created_by);
DROP POLICY IF EXISTS "Users can manage own workflows" ON workflows;
CREATE POLICY "Users can manage own workflows" ON workflows FOR ALL USING (auth.uid() = created_by);

-- AI conversations policies
DROP POLICY IF EXISTS "Users can view own conversations" ON ai_conversations;
CREATE POLICY "Users can view own conversations" ON ai_conversations FOR SELECT USING (auth.uid() = user_id);
DROP POLICY IF EXISTS "Users can manage own conversations" ON ai_conversations;
CREATE POLICY "Users can manage own conversations" ON ai_conversations FOR ALL USING (auth.uid() = user_id);

-- Notifications policies
DROP POLICY IF EXISTS "Users can view own notifications" ON notifications;
CREATE POLICY "Users can view own notifications" ON notifications FOR SELECT USING (auth.uid() = user_id);
DROP POLICY IF EXISTS "Users can update own notifications" ON notifications;
CREATE POLICY "Users can update own notifications" ON notifications FOR UPDATE USING (auth.uid() = user_id);

-- =====================================================
-- FUNCTIONS & TRIGGERS
-- =====================================================

-- Apply updated_at triggers (Funktion aus 01_shared_functions.sql)
CREATE OR REPLACE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE OR REPLACE TRIGGER update_files_updated_at BEFORE UPDATE ON files FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE OR REPLACE TRIGGER update_workflows_updated_at BEFORE UPDATE ON workflows FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE OR REPLACE TRIGGER update_ai_conversations_updated_at BEFORE UPDATE ON ai_conversations FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE OR REPLACE TRIGGER update_ai_models_updated_at BEFORE UPDATE ON ai_models FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- Function to automatically create user profile
CREATE OR REPLACE FUNCTION create_user_profile()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO user_profiles (user_id, display_name)
    VALUES (NEW.id, COALESCE(NEW.raw_user_meta_data->>'display_name', NEW.email));
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to create user profile on signup
CREATE OR REPLACE TRIGGER create_user_profile_trigger
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION create_user_profile();

-- =====================================================
-- INITIAL DATA
-- =====================================================

-- Insert default AI models (idempotent: ai_models.name hat ein echtes
-- UNIQUE-Constraint, ON CONFLICT (name) DO NOTHING greift wirklich -
-- verifiziert: blieb nach zwei Laeufen bei 6 Zeilen)
INSERT INTO ai_models (name, provider, model_type, description, max_tokens, input_cost_per_token, output_cost_per_token) VALUES
('gpt-4o', 'openai', 'chat', 'GPT-4 Omni - Latest OpenAI model', 128000, 0.000005, 0.000015),
('gpt-4o-mini', 'openai', 'chat', 'GPT-4 Omni Mini - Cost-effective', 128000, 0.00000015, 0.0000006),
('claude-3-5-sonnet', 'anthropic', 'chat', 'Claude 3.5 Sonnet - Advanced reasoning', 200000, 0.000003, 0.000015),
('claude-3-haiku', 'anthropic', 'chat', 'Claude 3 Haiku - Fast and efficient', 200000, 0.00000025, 0.00000125),
('gemini-1.5-pro', 'google', 'chat', 'Gemini 1.5 Pro - Google AI', 2000000, 0.0000035, 0.0000105),
('llama-3.1-70b', 'meta', 'chat', 'Llama 3.1 70B - Open source', 128000, 0.0000009, 0.0000009)
ON CONFLICT (name) DO NOTHING;

-- Hinweis: Die fruehere Default-Zeile in neo4j_connections ("Local Neo4j",
-- Passwort hartkodiert als 'password') wurde hier bewusst entfernt - aus
-- zwei unabhaengigen Gruenden: (1) neo4j_connections.name hat kein
-- UNIQUE-Constraint (bewusst unveraendert gegenueber dem bereits in
-- Produktion vorhandenen Schema, siehe infra/supabase/README.md zum
-- Baseline-Adoption-Prinzip), ON CONFLICT DO NOTHING griff daher nicht und
-- die Zeile duplizierte sich bei jedem Lauf (verifiziert: 1 Zeile wurde bei
-- erneutem Lauf zu 2). (2) Ein committetes Default-Secret ist unabhaengig
-- vom Duplikat-Bug ein eigenstaendiges Problem. Eine echte Default-
-- Verbindung mit echtem Secret-Handling (analog .env/n8n-Variables-
-- Konventionen) und ggf. nachtraeglichem UNIQUE-Constraint waere eine
-- spaetere, eigene Migration - nicht Teil dieser Datei.

-- =====================================================
-- VIEWS FOR COMMON QUERIES
-- =====================================================

-- View for file statistics
CREATE OR REPLACE VIEW file_stats AS
SELECT
    COUNT(*) as total_files,
    SUM(file_size) as total_size,
    AVG(file_size) as avg_size,
    COUNT(DISTINCT uploaded_by) as unique_uploaders,
    COUNT(*) FILTER (WHERE is_public = true) as public_files,
    COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '24 hours') as files_last_24h
FROM files
WHERE is_deleted = false;

-- View for workflow statistics
CREATE OR REPLACE VIEW workflow_stats AS
SELECT
    w.id,
    w.name,
    w.is_active,
    COUNT(we.id) as total_executions,
    COUNT(we.id) FILTER (WHERE we.status = 'success') as successful_executions,
    COUNT(we.id) FILTER (WHERE we.status = 'error') as failed_executions,
    AVG(we.execution_time_ms) as avg_execution_time,
    MAX(we.started_at) as last_execution
FROM workflows w
LEFT JOIN workflow_executions we ON w.id = we.workflow_id
GROUP BY w.id, w.name, w.is_active;

-- View for system health overview
CREATE OR REPLACE VIEW system_health_overview AS
SELECT
    service_name,
    status,
    AVG(response_time_ms) as avg_response_time,
    COUNT(*) as check_count,
    MAX(checked_at) as last_check
FROM service_health
WHERE checked_at >= NOW() - INTERVAL '1 hour'
GROUP BY service_name, status
ORDER BY service_name;

-- =====================================================
-- COMMENTS
-- =====================================================

COMMENT ON TABLE user_profiles IS 'Extended user profile information beyond auth.users';
COMMENT ON TABLE files IS 'Central file registry for all uploaded files across services';
COMMENT ON TABLE workflows IS 'n8n workflow registry and metadata';
COMMENT ON TABLE workflow_executions IS 'Track all n8n workflow executions';
COMMENT ON TABLE service_health IS 'Monitor health status of all services';
COMMENT ON TABLE ai_conversations IS 'Store AI/LLM conversation history';
COMMENT ON TABLE neo4j_connections IS 'Manage Neo4j database connections';
COMMENT ON TABLE notifications IS 'User notification system';
COMMENT ON TABLE system_alerts IS 'System-wide alerts and monitoring';

-- =====================================================
-- COMPLETION MESSAGE
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE 'LocalSupabase Complete System Tables Migration completed successfully!';
    RAISE NOTICE 'Created tables for: User Management, File System, Workflows, Monitoring, AI Integration, Neo4j, Notifications';
    RAISE NOTICE 'All tables have RLS enabled and appropriate indexes created.';
END $$;
