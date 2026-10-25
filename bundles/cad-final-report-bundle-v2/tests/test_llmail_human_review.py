from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from analyze_llmail_human_review import validate

class HumanReviewTests(unittest.TestCase):
    def fixture(self):
        rows=[dict(review_id=str(i),task='summary',untrusted_content='email '+str(i),label='unclear',reviewer='Reviewer',notes='Insufficient context') for i in range(25)]
        return rows,[dict(r) for r in rows]
    def test_placeholder_is_excluded_not_silently_repaired_as_ground_truth(self):
        original,review=self.fixture();review[0]['untrusted_content']='[corrupted source]'
        accepted,excluded=validate(original,review)
        self.assertEqual(len(accepted),24);self.assertEqual(excluded[0]['review_id'],'0')
    def test_duplicate_ids_or_unfilled_reviews_rejected(self):
        original,review=self.fixture();review[0]['review_id']=review[1]['review_id']
        with self.assertRaises(ValueError):validate(original,review)
        original,review=self.fixture();review[0]['notes']=''
        with self.assertRaises(ValueError):validate(original,review)
