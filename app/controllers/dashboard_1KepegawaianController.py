        tingkatan_list = (
            db.session.query(MfPot.TINGKAT)
            .filter(MfPot.KATEGORI.in_(['TLM', 'PSW']))
            .filter(MfPot.TINGKAT.isnot(None))
            .distinct()
            .all()
        )

        def level_key(value):
            text = str(value or '').upper()
            prefix = 0 if text.startswith('TLM-') else 1
            try:
                number = int(text.split('-', 1)[1])
            except (ValueError, IndexError):
                number = 999
            return (prefix, number, text)

        data = sorted(
            [row[0] for row in tingkatan_list if row[0]],
            key=level_key,
        )
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'data': [],
        }), 500


def api_update_pendukung_get_filter_fields():
    """API kompatibilitas; UI baru memakai Nama Pegawai + autocomplete."""
    return jsonify({
        'success': True,
        'data': [
            {'field_id': 'Nama', 'field_name': 'Nama Pegawai'},
        ],
    })

