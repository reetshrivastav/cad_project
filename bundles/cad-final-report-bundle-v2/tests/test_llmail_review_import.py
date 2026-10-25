from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from export_llmail_label_review import choose
from compare_llmail_label_review import compare

class ReviewImportTests(unittest.TestCase):
    def fixture(self):
        rows=[dict(id=str(i),split='validation',source_attack_attempt='False' if i<40 else 'True',source_reason='judge',task='query',untrusted_content='text '+str(i),component_sha256='g') for i in range(80)]
        review=[dict(review_id=f'LLMAIL-REVIEW-{i:03}',task=r['task'],untrusted_content=r['untrusted_content'],label='unclear',reviewer='AI-only',notes='Ambiguous target') for i,r in enumerate(choose(rows),1)]
        return rows,review
    def test_unclear_and_ai_provenance_not_recast_as_ground_truth(self):
        rows,review=self.fixture();result=compare(rows,review)
        self.assertEqual(result['source_label_vs_review'],{'False/unclear':40,'True/unclear':40})
        self.assertFalse(result['training_performed'])
        self.assertEqual(result['reviewers'],{'AI-only':80})
    def test_changed_text_or_duplicate_id_rejected(self):
        rows,review=self.fixture();review[0]['untrusted_content']='altered'
        with self.assertRaises(ValueError):compare(rows,review)
        rows,review=self.fixture();review[0]['review_id']=review[1]['review_id']
        with self.assertRaises(ValueError):compare(rows,review)
