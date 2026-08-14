-- Dedizierte Least-Privilege-Rolle fuer den n8n-Sync-Workflow
-- (n8n-tool-workflows/intune-device-sync.json).
--
-- Vorher war fuer diesen Workflow der postgres-Superuser als n8n-Postgres-
-- Credential dokumentiert (Muster wie bei anderen, aelteren n8n-Workflows
-- im Projekt) - fuer einen produktiven Sync-Workflow zu weitreichend.
--
-- Workflow-Analyse (n8n-tool-workflows/intune-device-sync.json, einziger
-- Postgres-Node "Upsert intune_devices"):
--   operation: "upsert", schema: "public", table: "intune_devices",
--   matchingColumns: ["intune_device_id"]
-- n8n erzeugt daraus eine einzelne Anweisung der Form
--   INSERT INTO public.intune_devices (...) VALUES (...)
--   ON CONFLICT (intune_device_id) DO UPDATE SET ...
-- Es gibt im Workflow keinen weiteren Postgres-Node und keinen DELETE.
--
-- WICHTIG, empirisch korrigiert (erste Fassung dieser Migration nahm an,
-- SELECT sei nicht noetig - das war FALSCH, real gegen eine disposable
-- PostgreSQL-15-Instanz widerlegt): Mit ausschliesslich INSERT+UPDATE
-- schlaegt der Upsert unter aktivem Row Level Security mit "permission
-- denied for table intune_devices" fehl, obwohl EXCLUDED nur die
-- vorgeschlagene Zeile referenziert. Ursache: Unter RLS muss Postgres beim
-- ON-CONFLICT-Pfad pruefen koennen, ob die ggf. bereits vorhandene Zeile
-- fuer die aufrufende Rolle sichtbar ist (RLS-Row-Visibility=SELECT-
-- Ebene), unabhaengig davon, dass der SQL-Text selbst keine SELECT-
-- Anweisung enthaelt. Deshalb zusaetzlich SELECT auf genau diese eine
-- Tabelle - weiterhin: kein DELETE, kein CREATE, keine anderen Tabellen,
-- kein Superuser/BYPASSRLS/Owner. Alle vier Faelle (erlaubter Upsert,
-- verweigertes SELECT-only vor diesem Fix, verweigertes DELETE, verweigerter
-- Zugriff auf andere Tabellen) real gegen eine disposable Instanz verifiziert,
-- siehe Testprotokoll in der zugehoerigen PR-Beschreibung.
--
-- Voraussetzung: 05_intune_devices.sql (Tabelle public.intune_devices).
-- Migration 05 selbst wird hier NICHT veraendert.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'intune_sync_writer') THEN
        CREATE ROLE intune_sync_writer NOLOGIN;
    END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO intune_sync_writer;
GRANT SELECT, INSERT, UPDATE ON public.intune_devices TO intune_sync_writer;

-- Table-Level-GRANTs allein reichen nicht: 05_intune_devices.sql aktiviert
-- Row Level Security auf intune_devices, und die einzige vorhandene Policy
-- ist auf service_role beschraenkt (RLS ist default-deny fuer jede Rolle
-- ohne passende Policy). Drei separate Policies (nicht FOR ALL), damit die
-- RLS-Ebene exakt bei den tatsaechlich gewaehrten Table-Grants bleibt (kein
-- DELETE ueber die Policy erlaubt, selbst wenn spaeter versehentlich ein
-- DELETE-Grant vergeben wuerde).
DROP POLICY IF EXISTS "Allow intune_sync_writer to select" ON public.intune_devices;
CREATE POLICY "Allow intune_sync_writer to select"
    ON public.intune_devices
    FOR SELECT
    TO intune_sync_writer
    USING (true);

DROP POLICY IF EXISTS "Allow intune_sync_writer to insert" ON public.intune_devices;
CREATE POLICY "Allow intune_sync_writer to insert"
    ON public.intune_devices
    FOR INSERT
    TO intune_sync_writer
    WITH CHECK (true);

DROP POLICY IF EXISTS "Allow intune_sync_writer to update" ON public.intune_devices;
CREATE POLICY "Allow intune_sync_writer to update"
    ON public.intune_devices
    FOR UPDATE
    TO intune_sync_writer
    USING (true)
    WITH CHECK (true);

COMMENT ON ROLE intune_sync_writer IS 'Least-Privilege-Rolle fuer den n8n-Sync-Workflow intune-device-sync.json (Upsert-Node: INSERT ... ON CONFLICT (intune_device_id) DO UPDATE). NOLOGIN per Default - Passwort wird bewusst nicht hier gesetzt (kein Secret im Git-Verlauf), sondern einmalig manuell per ALTER ROLE intune_sync_writer WITH LOGIN PASSWORD, siehe docs/28_intune_inventory.md. SELECT/INSERT/UPDATE auf public.intune_devices (SELECT empirisch als noetig fuer ON CONFLICT DO UPDATE unter RLS verifiziert) - kein DELETE/CREATE, keine anderen Tabellen.';
