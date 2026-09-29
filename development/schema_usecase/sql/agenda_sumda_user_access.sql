-- HRIS Reborn
-- Central User Account authorization definitions for Agenda + SUMDA.
-- These records make the three menu permissions selectable from:
--   /master/user
--
-- FormType=Transaksi and Model=2 are required by the existing
-- Master User / HAK_AKSES_FORM workflow.

INSERT INTO MF_FORM (
    FormID,
    Formname,
    FormType,
    Modul,
    Model
)
SELECT 'SUMDA_KESAMAPTAAN',
       'SUMDA - Kesamaptaan',
       'Transaksi',
       'HRIS',
       2
WHERE NOT EXISTS (
    SELECT 1 FROM MF_FORM WHERE FormID = 'SUMDA_KESAMAPTAAN'
);

INSERT INTO MF_FORM (
    FormID,
    Formname,
    FormType,
    Modul,
    Model
)
SELECT 'AGENDA_RAPAT',
       'AGENDA - Rapat',
       'Transaksi',
       'HRIS',
       2
WHERE NOT EXISTS (
    SELECT 1 FROM MF_FORM WHERE FormID = 'AGENDA_RAPAT'
);

INSERT INTO MF_FORM (
    FormID,
    Formname,
    FormType,
    Modul,
    Model
)
SELECT 'AGENDA_DISPOSISI',
       'AGENDA - Disposisi',
       'Transaksi',
       'HRIS',
       2
WHERE NOT EXISTS (
    SELECT 1 FROM MF_FORM WHERE FormID = 'AGENDA_DISPOSISI'
);

SELECT FormID, Formname, FormType, Modul, Model
FROM MF_FORM
WHERE FormID IN (
    'SUMDA_KESAMAPTAAN',
    'AGENDA_RAPAT',
    'AGENDA_DISPOSISI'
)
ORDER BY FormID;
