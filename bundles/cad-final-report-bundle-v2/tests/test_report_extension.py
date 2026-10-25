import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from analyze_report_extension import analyze
ARCHIVE=ROOT/'reports/evidence/report_extension_20261024/cad-report-extension-v1.tar.gz'

class ExtensionEvidenceTests(unittest.TestCase):
    def test_coverage_and_negative_results_are_retained(self):
        result=analyze(ARCHIVE)
        self.assertEqual(result['long_email']['windows'],723)
        self.assertEqual(result['long_email']['content_tokens_covered'],130735)
        self.assertEqual(result['long_email']['models']['pair']['max_window']['original_cutoff']['fp'],22)
        self.assertEqual(result['phase2']['status'],'failed_before_predictions')
    def test_missing_tail_window_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'changed.tar.gz'
            with tarfile.open(ARCHIVE) as source,tarfile.open(path,'w:gz') as out:
                for member in source:
                    if member.isdir():out.addfile(member);continue
                    data=source.extractfile(member).read()
                    if member.name.endswith('long_email_result.json'):
                        result=json.loads(data);result['models']['pair']['rows'][0]['window_intervals'][-1][1]-=1;data=json.dumps(result).encode()
                    member.size=len(data);out.addfile(member,io.BytesIO(data))
            with self.assertRaises(ValueError):analyze(path)
