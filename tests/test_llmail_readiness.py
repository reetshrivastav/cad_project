from pathlib import Path
import sqlite3
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from check_llmail_readiness import screen,tokens,jaccard

class ReadinessTests(unittest.TestCase):
    def test_detects_cross_split_reordered_content(self):
        connection=sqlite3.connect(':memory:')
        rows=[dict(id='a',split='train',untrusted_content='Alpha beta gamma'),dict(id='b',split='test',untrusted_content='GAMMA beta alpha')]
        result=screen(connection,rows);connection.close()
        self.assertEqual(result['pairs_jaccard_ge_0_8'],{'test/train':1})
        self.assertEqual(result['rows_in_detected_pairs'],2)

    def test_caps_are_reported(self):
        rows=[dict(id=str(i),split='train' if i<3 else 'test',untrusted_content='same text') for i in range(4)]
        connection=sqlite3.connect(':memory:');result=screen(connection,rows,bucket_cap=1);connection.close()
        self.assertGreater(result['skipped_overfull_anchor_queries'],0)
        connection=sqlite3.connect(':memory:');result=screen(connection,rows,pair_cap=0);connection.close()
        self.assertTrue(result['pair_budget_exhausted'])

    def test_token_overlap_is_lexical_not_semantic(self):
        self.assertLess(jaccard(tokens('send email'),tokens('do not send email')),1)
