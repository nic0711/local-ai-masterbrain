-- Create Intune Devices Table for Intune Device Inventory Reporting
--
-- Eigenstaendiges Reporting-Werkzeug, NICHT Teil der Intune-Policy-Hub-
-- Zielarchitektur (ADR-0001/0004/0005). Siehe docs/28_intune_inventory.md.
--
-- Voraussetzung: 01_shared_functions.sql (public.update_updated_at_column()).
-- Im Unterschied zu 02-04 ist dies eine echte NEUE Migration - die reale
-- Datenbank hat diese Tabelle bislang nicht (verifiziert per Bestandsaufnahme
-- gegen eine Kopie der Produktions-PGDATA).

-- Create the intune_devices table
CREATE TABLE IF NOT EXISTS public.intune_devices (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    intune_device_id TEXT NOT NULL UNIQUE,
    device_name TEXT,
    operating_system TEXT,
    os_version TEXT,
    model TEXT,
    manufacturer TEXT,
    physical_memory_bytes BIGINT,
    processor_architecture TEXT,
    primary_user_upn TEXT,
    primary_user_display_name TEXT,
    compliance_state TEXT,
    last_sync_date_time TIMESTAMP WITH TIME ZONE,
    raw_metadata JSONB DEFAULT '{}',
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_intune_devices_primary_user_upn ON public.intune_devices(primary_user_upn);
CREATE INDEX IF NOT EXISTS idx_intune_devices_compliance_state ON public.intune_devices(compliance_state);
CREATE INDEX IF NOT EXISTS idx_intune_devices_os_version ON public.intune_devices(os_version);

-- updated_at trigger (Funktion aus 01_shared_functions.sql)
CREATE OR REPLACE TRIGGER update_intune_devices_updated_at
    BEFORE UPDATE ON public.intune_devices
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- Enable Row Level Security (RLS)
ALTER TABLE public.intune_devices ENABLE ROW LEVEL SECURITY;

-- Allow service role to do everything (for n8n sync writes). DROP IF EXISTS
-- + CREATE statt nacktem CREATE POLICY: Postgres kennt kein CREATE POLICY
-- IF NOT EXISTS.
DROP POLICY IF EXISTS "Allow service role full access" ON public.intune_devices;
CREATE POLICY "Allow service role full access"
    ON public.intune_devices
    FOR ALL
    TO service_role
    USING (true);

-- Grant permissions
GRANT ALL ON public.intune_devices TO service_role;

-- Dedizierte, least-privilege Read-only-Rolle fuer die Grafana-Datasource.
-- Angelegt ohne Login/Passwort - das Passwort wird bewusst NICHT hier
-- gesetzt (kein Secret im Git-Verlauf), sondern einmalig manuell per
-- `ALTER ROLE ... WITH LOGIN PASSWORD '...'`, siehe docs/28_intune_inventory.md.
-- Idempotent angelegt, da Postgres kein natives CREATE ROLE IF NOT EXISTS
-- kennt (Standard-Idiom via DO-Block + pg_roles-Check).
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'grafana_intune_reader') THEN
        CREATE ROLE grafana_intune_reader NOLOGIN;
    END IF;
END
$$;
GRANT USAGE ON SCHEMA public TO grafana_intune_reader;
GRANT SELECT ON public.intune_devices TO grafana_intune_reader;

-- Add comments for documentation
COMMENT ON TABLE public.intune_devices IS 'Geraete-Inventar aus Microsoft Intune (Graph API /deviceManagement/managedDevices, v1.0), befuellt durch n8n-Workflow intune-device-sync.json. Eigenstaendiges Reporting, nicht Teil der Intune-Policy-Hub-Zielarchitektur (ADR-0001/0004/0005). processor_architecture ist die Datengrenze des v1.0-Endpoints (kein CPU-Modell/Kernanzahl, siehe docs/28_intune_inventory.md).';
COMMENT ON COLUMN public.intune_devices.intune_device_id IS 'Graph API managedDevice.id, Basis fuer den Upsert im n8n-Sync';
COMMENT ON COLUMN public.intune_devices.physical_memory_bytes IS 'RAM in Bytes, Graph-Feld physicalMemoryInBytes';
COMMENT ON COLUMN public.intune_devices.processor_architecture IS 'Nur Architektur (x64/arm64/x86), Graph liefert im v1.0-Endpoint kein CPU-Modell';
COMMENT ON COLUMN public.intune_devices.raw_metadata IS 'Unverarbeitete Graph-Restfelder aus dem jeweiligen Sync-Lauf';
COMMENT ON COLUMN public.intune_devices.synced_at IS 'Zeitpunkt des letzten n8n-Sync-Laufs fuer diesen Datensatz';
