-- Create OCR Results Table for TrOCR Service
--
-- Voraussetzung: 01_shared_functions.sql (public.update_updated_at_column()).

-- Create the ocr_results table
CREATE TABLE IF NOT EXISTS public.ocr_results (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    request_id UUID NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    engine_used TEXT NOT NULL CHECK (engine_used IN ('trocr', 'tesseract', 'auto')),
    processing_time DECIMAL(10,3) NOT NULL,
    confidence_score DECIMAL(5,3) NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    text TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_ocr_results_request_id ON public.ocr_results(request_id);
CREATE INDEX IF NOT EXISTS idx_ocr_results_filename ON public.ocr_results(filename);
CREATE INDEX IF NOT EXISTS idx_ocr_results_engine_used ON public.ocr_results(engine_used);
CREATE INDEX IF NOT EXISTS idx_ocr_results_confidence_score ON public.ocr_results(confidence_score);
CREATE INDEX IF NOT EXISTS idx_ocr_results_created_at ON public.ocr_results(created_at);

-- updated_at trigger (Funktion aus 01_shared_functions.sql)
CREATE OR REPLACE TRIGGER update_ocr_results_updated_at
    BEFORE UPDATE ON public.ocr_results
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- Enable Row Level Security (RLS)
ALTER TABLE public.ocr_results ENABLE ROW LEVEL SECURITY;

-- Create policies for RLS. DROP IF EXISTS + CREATE statt nacktem CREATE
-- POLICY: Postgres kennt kein CREATE POLICY IF NOT EXISTS, das ist das
-- Standard-Idiom fuer idempotente Policy-Definitionen.

-- Allow authenticated users to read all OCR results
DROP POLICY IF EXISTS "Allow authenticated users to read OCR results" ON public.ocr_results;
CREATE POLICY "Allow authenticated users to read OCR results"
    ON public.ocr_results
    FOR SELECT
    TO authenticated
    USING (true);

-- Allow authenticated users to insert OCR results
DROP POLICY IF EXISTS "Allow authenticated users to insert OCR results" ON public.ocr_results;
CREATE POLICY "Allow authenticated users to insert OCR results"
    ON public.ocr_results
    FOR INSERT
    TO authenticated
    WITH CHECK (true);

-- Allow users to update their own OCR results (based on created_at being recent)
DROP POLICY IF EXISTS "Allow users to update recent OCR results" ON public.ocr_results;
CREATE POLICY "Allow users to update recent OCR results"
    ON public.ocr_results
    FOR UPDATE
    TO authenticated
    USING (created_at > NOW() - INTERVAL '1 hour');

-- Allow service role to do everything (for n8n and edge functions)
DROP POLICY IF EXISTS "Allow service role full access" ON public.ocr_results;
CREATE POLICY "Allow service role full access"
    ON public.ocr_results
    FOR ALL
    TO service_role
    USING (true);

-- Grant permissions
GRANT ALL ON public.ocr_results TO authenticated;
GRANT ALL ON public.ocr_results TO service_role;

-- Add comments for documentation
COMMENT ON TABLE public.ocr_results IS 'Stores results from TrOCR and Tesseract OCR processing';
COMMENT ON COLUMN public.ocr_results.request_id IS 'Unique identifier for the OCR request';
COMMENT ON COLUMN public.ocr_results.filename IS 'Original filename of the processed document';
COMMENT ON COLUMN public.ocr_results.engine_used IS 'OCR engine used: trocr, tesseract, or auto';
COMMENT ON COLUMN public.ocr_results.processing_time IS 'Time taken to process the document in seconds';
COMMENT ON COLUMN public.ocr_results.confidence_score IS 'OCR confidence score between 0 and 1';
COMMENT ON COLUMN public.ocr_results.text IS 'Extracted text content from the document';
COMMENT ON COLUMN public.ocr_results.metadata IS 'Additional metadata from the OCR processing';
