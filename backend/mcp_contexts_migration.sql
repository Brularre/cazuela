CREATE TABLE mcp_contexts (
    context_id uuid PRIMARY KEY,
    version text NOT NULL DEFAULT '1.0',
    domain text NOT NULL,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    status text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'staged', 'confirmed', 'rolled_back')),
    payload jsonb NOT NULL DEFAULT '{}',
    proposed jsonb,
    agent_model text NOT NULL DEFAULT 'stub-v1',
    iteration_count integer NOT NULL DEFAULT 0
);

-- Index for the most common query: find staged contexts for a user
CREATE INDEX idx_mcp_contexts_user_status ON mcp_contexts (user_id, status);

-- Index for TTL pruning
CREATE INDEX idx_mcp_contexts_expires_at ON mcp_contexts (expires_at);

-- RLS
ALTER TABLE mcp_contexts ENABLE ROW LEVEL SECURITY;
CREATE POLICY mcp_contexts_user_isolation ON mcp_contexts
    FOR ALL USING (user_id = auth.uid());
