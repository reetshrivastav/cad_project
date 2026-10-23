import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from analyze_context_v2 import analyze
from evaluate_context_v2_transfer import load_cases
ARCHIVE=ROOT/'reports/evidence/context_v2_scoring_20261023/context-v2-lab-results.tar.gz'

class ContextEvidenceTests(unittest.TestCase):
    def test_recorded_evidence_reconciles(self):
        result=analyze(ARCHIVE)
        self.assertEqual(result['models']['pair']['false_review'],1)
        self.assertEqual(result['models']['pair']['true_review'],24)
        self.assertEqual(result['pair_errors'][0]['id'],'CTX-032-01')

    def test_changed_metrics_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'changed.tar.gz'
            with tarfile.open(ARCHIVE) as source,tarfile.open(target,'w:gz') as out:
                for member in source:
                    if member.isdir():out.addfile(member);continue
                    data=source.extractfile(member).read()
                    if member.name=='results/context_v2_topic_test.json':
                        result=json.loads(data);result['models']['pair']['metrics']['false_review']=0
                        data=json.dumps(result).encode()
                    member.size=len(data);out.addfile(member,io.BytesIO(data))
            with self.assertRaisesRegex(ValueError,'Test metrics mismatch'):analyze(target)

    def test_transfer_is_separate_and_has_task_contrasts(self):
        rows=load_cases();self.assertEqual(len(rows),48)
        self.assertEqual(sum(r['label']=='review_redirection' for r in rows),16)
        original={json.loads(line)['untrusted_content'] for line in (ROOT/'reports/evidence/context_v2_preparation_20261023/cases.jsonl').read_text().splitlines()}
        self.assertFalse(original & {r['untrusted_content'] for r in rows})
        for group in {r['group_id'] for r in rows}:
            redirected=[r for r in rows if r['group_id']==group and r['content_kind']=='redirection']
            self.assertEqual(len({r['untrusted_content'] for r in redirected}),1)
            self.assertEqual({r['label'] for r in redirected},{'allow_task','review_redirection'})
