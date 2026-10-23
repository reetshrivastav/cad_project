import json
from pathlib import Path
import sys
import tempfile
import unittest
import io
import tarfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from evaluate_llmail_benign import select_rows,summarize
from analyze_llmail_training import analyze
ARCHIVE=ROOT/'reports/evidence/llmail_short_training_20261023/llmail-short-training-v1.tar.gz'

class Tokenizer:
    def __call__(self,texts,**kwargs):return {'input_ids':[[0]*len(t.split()) for t in texts]}

class BenignDiagnosticTests(unittest.TestCase):
    def test_overlap_duplicates_and_lengths_are_excluded_explicitly(self):
        rows,counts,_=select_rows(['known email','Known EMAIL','word '*257,'short email'],'Summarize',{'known email'},Tokenizer())
        self.assertEqual([r['untrusted_content'] for r in rows],['short email'])
        self.assertEqual(counts,{'normalized_exact_development_overlap':1,'duplicate_in_benign_collection':1,'over_256_tokens':1})

    def test_fixed_cutoff_and_probabilities(self):
        self.assertEqual(summarize([.49,.5,1])['flagged_publisher_benign'],2)
        with self.assertRaises(ValueError):summarize([float('nan')])

    def test_training_evidence_reconciles(self):
        result=analyze(ARCHIVE)
        self.assertEqual(result['models']['pair']['validation']['fp'],34)
        self.assertEqual(result['models']['content_only']['validation']['tn'],7)

    def test_changed_training_metric_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'changed.tar.gz'
            with tarfile.open(ARCHIVE) as source,tarfile.open(target,'w:gz') as out:
                for member in source:
                    if member.isdir():out.addfile(member);continue
                    data=source.extractfile(member).read()
                    if member.name.endswith('training_report.json'):
                        report=json.loads(data);report['models']['pair']['validation']['fp']=0;data=json.dumps(report).encode()
                    member.size=len(data);out.addfile(member,io.BytesIO(data))
            with self.assertRaises(ValueError):analyze(target)
