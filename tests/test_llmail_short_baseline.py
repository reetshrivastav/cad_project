from pathlib import Path
import sqlite3
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_llmail_short_baseline import bands,cleanup

class ShortBaselineTests(unittest.TestCase):
    def test_exact_cleanup_is_complete_and_preserves_reserved_priority(self):
        rows=[dict(id='a',split='train',untrusted_content='alpha beta gamma'),dict(id='b',split='validation',untrusted_content='ALPHA beta gamma'),dict(id='c',split='test',untrusted_content='gamma beta alpha')]
        connection=sqlite3.connect(':memory:');result=cleanup(connection,rows)
        self.assertEqual({r[0] for r in connection.execute('SELECT id FROM excluded')},{'a','b'})
        self.assertEqual(result['surviving_normalized_exact_keys_cross_splits'],0);connection.close()

    def test_budget_overflow_excludes_candidates_instead_of_skipping(self):
        rows=[dict(id='a',split='train',untrusted_content='alpha beta'),dict(id='b',split='test',untrusted_content='alpha beta')]
        connection=sqlite3.connect(':memory:');result=cleanup(connection,rows,pair_budget=0)
        self.assertGreater(result['counts']['conservatively_excluded_candidate_edges'],0)
        self.assertEqual(connection.execute('SELECT id FROM excluded').fetchall(),[('a',)]);connection.close()

    def test_bands_are_deterministic_and_order_independent(self):
        self.assertEqual(bands({'alpha','beta'}),bands(set(['beta','alpha'])))
        self.assertEqual(len(bands({'alpha'})),16)
