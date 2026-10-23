import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import evaluate_injection_candidate as candidate


class CandidateTests(unittest.TestCase):
    def test_diagnostic_corpora_match_frozen_results(self):
        cases = candidate.load_cases()
        self.assertEqual(len(cases),276)
        for group,count in [('benign_ai',200),('bipia_attack',75),('bipia_control',1)]:
            self.assertEqual(sum(r['group']==group for r in cases),count)

    def test_label_index_comes_from_config_not_assumed_position(self):
        self.assertEqual(candidate.injection_label_index({0:'SAFE',1:'INJECTION'}),1)
        self.assertEqual(candidate.injection_label_index({'0':'INJECTION','1':'SAFE'}),0)
        with self.assertRaises(ValueError):
            candidate.injection_label_index({0:'LABEL_0',1:'LABEL_1'})

    def test_errors_and_strict_threshold_boundaries_are_visible(self):
        cases = [{'id':str(i),'group':'benign_ai','prompt':'example','baseline_normal_tier':'full'} for i in range(4)]
        scores = iter([.92,.921,float('nan'),.5])
        rows = candidate.run_cases(cases,lambda _: {'injection_probability':next(scores)})
        high = candidate.summary(rows,.92)['groups']['benign_ai']
        self.assertEqual(high['offered'],4)
        self.assertEqual(high['errors'],1)
        self.assertEqual(high['scored'],3)
        self.assertEqual(high['flagged'],1)
        self.assertEqual(candidate.summary(rows,.5)['groups']['benign_ai']['flagged'],2)

    def test_all_failed_group_has_no_false_success_fraction(self):
        row = {'group':'bipia_attack','baseline_normal_tier':'full','error':'failed'}
        result = candidate.summary([row],.92)['groups']['bipia_attack']
        self.assertIsNone(result['flagged_fraction_of_scored'])
        self.assertEqual(result['errors'],1)
