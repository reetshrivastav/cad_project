import copy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import analyze_injection_candidate as analysis


class CandidateEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((ROOT/'reports/evidence/injection_candidate_scoring_20261023/injection_candidate_shadow_v1.json').read_text())

    def test_clean_control_failure_is_retained_with_attack_flags(self):
        result=analysis.verify(self.data)
        self.assertEqual(result['verified_rows'],276)
        self.assertTrue(result['primary_clean_control_flagged'])
        self.assertFalse(result['weight_digest_independently_rehashed'])
        groups=result['comparisons'][0]['groups']
        self.assertEqual(groups['benign_ai']['flagged'],0)
        self.assertEqual(groups['bipia_attack']['flagged'],75)
        self.assertEqual(groups['bipia_control']['flagged'],1)

    def test_model_source_and_card_changes_are_rejected(self):
        for field in ('model_revision','script_sha256','model_card_snapshot'):
            data=copy.deepcopy(self.data);data[field]='changed'
            with self.assertRaises(ValueError):analysis.verify(data)

    def test_control_removal_probability_and_metrics_changes_are_rejected(self):
        for change in ('control','probability','summary'):
            data=copy.deepcopy(self.data)
            if change=='control':data['rows']=[r for r in data['rows'] if r['group']!='bipia_control']
            elif change=='probability':data['rows'][0]['injection_probability']=float('nan')
            else:data['comparisons'][0]['groups']['bipia_control']['flagged']=0
            with self.assertRaises(ValueError):analysis.verify(data)
