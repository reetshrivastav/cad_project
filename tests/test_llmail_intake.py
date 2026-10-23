import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('llmail_intake',ROOT/'scripts/download_llmail_phase1.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class LlmailIntakeTests(unittest.TestCase):
    def test_raw_schema_preserves_team_and_scenario_statistics(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'raw.jsonl'
            rows=[dict(team_id='team-a',scenario='level1a',body='secret payload',subject='subject'),dict(scenario='level2b',body='x')]
            path.write_text(''.join(json.dumps(r)+'\n' for r in rows));summary=m.summarize(path)
        self.assertEqual(summary['rows'],2);self.assertEqual(summary['missing_team'],1)
        self.assertEqual(summary['unique_teams'],1)
        self.assertNotIn('secret payload',json.dumps(summary))

    def test_annotations_remain_source_values_not_new_ground_truth(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'labelled_unique_submissions_phase1.json'
            path.write_text(json.dumps({'payload':{'attack_attempt':'False','reason':'judge'}}));summary=m.summarize(path)
        self.assertEqual(summary['attack_attempt_values'],{'False':1})
        self.assertEqual(summary['annotation_reasons'],{'judge':1})
        self.assertFalse(any('phase2' in f for f in m.FILES))
