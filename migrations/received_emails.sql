-- Received emails table
CREATE TABLE IF NOT EXISTS public.received_emails (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    agent_email_id uuid REFERENCES public.agent_emails(id),
    from_email text NOT NULL,
    from_name text,
    subject text,
    text_content text,
    html_content text,
    headers jsonb DEFAULT '{}',
    forwarded_to text,
    status text DEFAULT 'received' CHECK (status IN ('received', 'forwarded', 'failed')),
    created_at timestamptz DEFAULT now()
);

-- Enable RLS
ALTER TABLE public.received_emails ENABLE ROW LEVEL SECURITY;

-- Policy
CREATE POLICY "Users can view own received emails" ON public.received_emails 
    FOR SELECT USING (
        agent_email_id IN (
            SELECT id FROM public.agent_emails WHERE user_id = auth.uid()
        )
    );
