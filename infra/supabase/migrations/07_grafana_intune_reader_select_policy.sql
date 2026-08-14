-- Fehlende RLS-Policy fuer grafana_intune_reader nachtragen.
--
-- Konkret nachgewiesener Fehler in der bereits gemergten Migration
-- 05_intune_devices.sql (wird hier NICHT veraendert, siehe Projekt-
-- konvention fuer bereits angewendete Migrationen): die Rolle bekommt dort
-- zwar `GRANT SELECT ON public.intune_devices TO grafana_intune_reader`,
-- aber 05 legt ausschliesslich eine RLS-Policy fuer service_role an. Unter
-- Row Level Security fuehrt eine fehlende Policy fuer SELECT NICHT zu einem
-- Fehler, sondern dazu, dass jede Abfrage still 0 Zeilen liefert - real
-- verifiziert gegen eine disposable PostgreSQL-15-Instanz: `SET ROLE
-- grafana_intune_reader; SELECT * FROM public.intune_devices;` lieferte
-- trotz gueltigem SELECT-Grant "(0 rows)". Ohne diese Migration waere das
-- Grafana-Dashboard dauerhaft leer, unabhaengig davon ob der n8n-Sync
-- tatsaechlich Daten schreibt.
--
-- Voraussetzung: 05_intune_devices.sql (Tabelle + Rolle grafana_intune_reader
-- existieren bereits, RLS ist dort bereits aktiviert).

DROP POLICY IF EXISTS "Allow grafana_intune_reader to select" ON public.intune_devices;
CREATE POLICY "Allow grafana_intune_reader to select"
    ON public.intune_devices
    FOR SELECT
    TO grafana_intune_reader
    USING (true);
