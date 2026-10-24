from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from evaluate_llmail_phase2 import projected_task,transfer_cohort,keys

class Phase2Tests(unittest.TestCase):
    def test_phase2_retrieval_levels_do_not_use_phase1_summary_mapping(self):
        scenarios={'scenario_1':{'user_query':'Summarize emails'},'scenario_3':{'user_query':'Summarize emails about Project Zenith.'},'scenario_4':{'user_query':'Summarize Q2 budget emails.'}}
        self.assertEqual(projected_task('level1k',scenarios)[0],'scenario_3')
        self.assertEqual(projected_task('level2v',scenarios)[0],'scenario_4')
        with self.assertRaises(ValueError):projected_task('level1a',scenarios)
    def test_one_known_owner_prevents_new_team_claim(self):
        self.assertFalse(transfer_cohort({'new','old'},{'old'}))
        self.assertTrue(transfer_cohort({'new'},{'old'}))
        self.assertFalse(transfer_cohort(set(),{'old'}))
    def test_normalized_text_and_token_bag_overlap_differ(self):
        a,b=keys('Alpha beta');c,d=keys('BETA alpha')
        self.assertNotEqual(a,c);self.assertEqual(b,d)
        self.assertEqual(keys('ALPHA   beta'),keys('alpha beta'))
