-- HRIS Reborn
-- Permission records for User Account.
-- TransacID is mandatory in the legacy MF_FORM schema.
-- Model=2 is required by the Master User operator-access list.

INSERT INTO MF_FORM (
    FormID, Formname, FormType, Nourut, Berkas, PanelPage, ImgUrl,
    NoUrutPanel, Modul, parentForm, Model, IconFA, HirarkiLvl, TransacID
)
SELECT
    'SUMDA_KESAMAPTAAN', 'SUMDA - Kesamaptaan', 'Transaksi', 1, 'input',
    'SUMDA', '-', 1, 'HRIS', '', 2, 'fa fa-heartbeat', 1,
    (SELECT COALESCE(MAX(TransacID), 0) + 1 FROM MF_FORM)
WHERE NOT EXISTS (SELECT 1 FROM MF_FORM WHERE FormID='SUMDA_KESAMAPTAAN');

INSERT INTO MF_FORM (
    FormID, Formname, FormType, Nourut, Berkas, PanelPage, ImgUrl,
    NoUrutPanel, Modul, parentForm, Model, IconFA, HirarkiLvl, TransacID
)
SELECT
    'AGENDA_RAPAT', 'AGENDA - Rapat', 'Transaksi', 1, 'input',
    'Agenda', '-', 1, 'HRIS', '', 2, 'fa fa-users', 1,
    (SELECT COALESCE(MAX(TransacID), 0) + 1 FROM MF_FORM)
WHERE NOT EXISTS (SELECT 1 FROM MF_FORM WHERE FormID='AGENDA_RAPAT');

INSERT INTO MF_FORM (
    FormID, Formname, FormType, Nourut, Berkas, PanelPage, ImgUrl,
    NoUrutPanel, Modul, parentForm, Model, IconFA, HirarkiLvl, TransacID
)
SELECT
    'AGENDA_DISPOSISI', 'AGENDA - Disposisi', 'Transaksi', 2, 'input',
    'Agenda', '-', 2, 'HRIS', '', 2, 'fa fa-send', 1,
    (SELECT COALESCE(MAX(TransacID), 0) + 1 FROM MF_FORM)
WHERE NOT EXISTS (SELECT 1 FROM MF_FORM WHERE FormID='AGENDA_DISPOSISI');

-- Existing installations may already contain the rows with Model=1.
-- Normalize them to the Model=2 convention used by Master User.
UPDATE MF_FORM
SET Model=2
WHERE FormID IN ('SUMDA_KESAMAPTAAN','AGENDA_RAPAT','AGENDA_DISPOSISI')
  AND Modul='HRIS';

SELECT FormID, Formname, FormType, Modul, Model, TransacID
FROM MF_FORM
WHERE FormID IN ('SUMDA_KESAMAPTAAN','AGENDA_RAPAT','AGENDA_DISPOSISI')
ORDER BY TransacID;
