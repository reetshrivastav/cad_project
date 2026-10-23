import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from analyze_context_v2_transfer import analyze_transfer
SOURCE=ROOT/'reports/evidence/context_v2_transfer_scoring_20261023/context_v2_wording_transfer.json'

class TransferEvidenceTests(unittest.TestCase):
    def test_recorded_misses_are_retained(self):
        result=analyze_transfer(SOURCE)
        self.assertEqual(result['models']['pair']['missed_review'],12)
        self.assertEqual(result['models']['pair']['false_review'],1)
        self.assertEqual(len(result['pair_errors']),13)

    def test_changed_inputs_models_and_metrics_rejected(self):
        for kind in ('input','model','metric'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as directory:
                result=json.loads(SOURCE.read_text())
                if kind=='input':result['models']['pair']['rows'][0]['task']='altered'
                elif kind=='model':result['artifact_sha256']['pair.ubj']='0'*64
                else:result['models']['pair']['metrics']['missed_review']=0
                path=Path(directory)/'changed.json';path.write_text(json.dumps(result))
                with self.assertRaises(ValueError):analyze_transfer(path)
