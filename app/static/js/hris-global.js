/* ============================================================
   HRIS REBORN
   GLOBAL UI JAVASCRIPT
   ============================================================

   File:
   app/static/js/hris-global.js

   Fungsi:
   - Standar dropdown filter HRIS.
   - Dipakai lintas halaman.
   - Tidak mengandung logic bisnis halaman tertentu.
   ============================================================ */

(function (window) {

    'use strict';

    const HRIS_FILTER_FIELDS = [
        {
            field_id: 'NIP',
            field_name: 'NIP'
        },
        {
            field_id: 'Nama',
            field_name: 'Nama'
        },
        {
            field_id: 'FingerID',
            field_name: 'FingerID'
        },
        {
            field_id: 'UnitKerja',
            field_name: 'Unit Kerja'
        }
    ];

    /**
     * Mengisi satu atau beberapa <select>
     * dengan standar field filter HRIS.
     *
     * Contoh:
     * hrisInitFilterFields('.hris-filter-field');
     */
    function hrisInitFilterFields(selector) {

        const elements = document.querySelectorAll(selector);

        elements.forEach(function (select) {

            const currentValue = select.value;

            select.innerHTML =
                '<option value="">- Pilih Field -</option>';

            HRIS_FILTER_FIELDS.forEach(function (field) {

                const option =
                    document.createElement('option');

                option.value = field.field_id;
                option.textContent = field.field_name;

                select.appendChild(option);
            });

            if (currentValue) {
                select.value = currentValue;
            }
        });
    }

    /**
     * Public API.
     */
    window.HRISGlobal = {
        filterFields: HRIS_FILTER_FIELDS,
        initFilterFields: hrisInitFilterFields
    };

})(window);
