import json
import unittest
from pbp_guard.intake import check_json

class TestIntakeBoundary(unittest.TestCase):
    def test_valid_synthetic_fixture(self):
        from pathlib import Path
        for path in (Path(__file__).parents[1] / 'fixtures/cases').glob('*.json'):
            self.assertEqual('', check_json(path.read_text()), path.name)

    def test_duplicate_key_cannot_hide_original_evidence(self):
        self.assertEqual('duplicate_field', check_json('{"evidence":{"paid":false,"paid":true}}'))

    def test_personal_data_not_persistable(self):
        self.assertEqual('personal_data_found', check_json('{"note":"email somebody@example.invalid"}'))

    def test_production_and_competing_payment_sources_refused(self):
        self.assertEqual('sandbox_required', check_json('{"environment":"production"}'))
        self.assertEqual('ambiguous_payment_fields', check_json('{"payments":[],"pix":[]}'))

    def test_size_and_depth_bounded(self):
        self.assertEqual('input_too_large', check_json(json.dumps({'x':'x'*70000})))
        self.assertNotEqual('', check_json('{"a":'*60 + 'null' + '}'*60))

    def test_invalid_top_level_and_json(self):
        for value in ['[]','null','true','{"x":NaN}','{"x":']:
            self.assertNotEqual('', check_json(value), value)
