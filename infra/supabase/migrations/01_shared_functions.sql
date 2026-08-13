-- Zentrale, einmalige Definition gemeinsam genutzter Trigger-Funktionen.
--
-- update_updated_at_column() wurde vorher in 02/03/04 redundant identisch
-- neu definiert (jeweils per CREATE OR REPLACE, daher harmlos, aber
-- unnoetige Duplikation). Ab hier gibt es nur noch diese eine Definition;
-- 02-05 setzen sie als Voraussetzung voraus und definieren sie nicht mehr
-- selbst.
--
-- Hinweis: In der Datenbank existiert bereits eine gleichnamige Funktion im
-- Schema "storage" (Supabase-intern, eigene Definition, eigener Zweck) -
-- das ist kein Konflikt, da Postgres Funktionen pro Schema unterscheidet.
-- Diese Datei betrifft ausschliesslich public.update_updated_at_column().

CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION public.update_updated_at_column() IS 'Gemeinsame updated_at-Trigger-Funktion fuer alle projekteigenen Tabellen (infra/supabase/migrations/02-05).';
