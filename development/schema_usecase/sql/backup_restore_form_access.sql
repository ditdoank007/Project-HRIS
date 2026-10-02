-- HRIS Reborn: permission definition for Backup / Restore
-- Run once on the HRIS MariaDB database.
-- Administrator does not require HAK_AKSES_FORM; operators can be granted
-- this form from Master File -> User Account.

INSERT INTO MF_FORM
    (FormID, Formname, FormType, Nourut, Berkas, PanelPage, ImgUrl,
     NoUrutPanel, Modul, parentForm, Model, IconFA, HirarkiLvl, TransacID)
SELECT
    'BackupRestore.aspx',
    'Backup / Restore',
    'Transaksi',
    NULL,
    'BackupRestore.aspx',
    NULL,
    NULL,
    NULL,
    'HRIS',
    NULL,
    2,
    'database',
    NULL,
    NULL
WHERE NOT EXISTS (
    SELECT 1
    FROM MF_FORM
    WHERE FormID = 'BackupRestore.aspx'
);

SELECT
    FormID,
    Formname,
    FormType,
    Modul,
    Model
FROM MF_FORM
WHERE FormID = 'BackupRestore.aspx';
