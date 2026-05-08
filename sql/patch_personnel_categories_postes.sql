-- Concept Personnel : Categorie -> Poste -> Personnel
-- A executer une fois sur les bases existantes si vous voulez preparer
-- le schema manuellement. L'application appelle aussi ces requetes au besoin.

CREATE TABLE IF NOT EXISTS public.tb_categoriepersonnel (
    idcategorie SERIAL PRIMARY KEY,
    titre VARCHAR(120) NOT NULL,
    description TEXT,
    dateregistre TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS public.tb_postepersonnel (
    idposte SERIAL PRIMARY KEY,
    idcategorie INTEGER REFERENCES public.tb_categoriepersonnel(idcategorie)
        ON UPDATE CASCADE ON DELETE SET NULL,
    titre VARCHAR(120) NOT NULL,
    description TEXT,
    dateregistre TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted INTEGER DEFAULT 0
);

ALTER TABLE public.tb_personnel
ADD COLUMN IF NOT EXISTS idposte INTEGER;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'tb_personnel_idposte_fkey'
    ) THEN
        ALTER TABLE public.tb_personnel
        ADD CONSTRAINT tb_personnel_idposte_fkey
        FOREIGN KEY (idposte)
        REFERENCES public.tb_postepersonnel(idposte)
        ON UPDATE CASCADE
        ON DELETE SET NULL
        NOT VALID;
    END IF;
END $$;
