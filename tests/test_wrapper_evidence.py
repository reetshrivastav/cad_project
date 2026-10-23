import copy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import analyze_wrapper_diagnostic as analysis


class WrapperEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((ROOT/'reports/evidence/wrapper_diagnostic_scoring_20261023/wrapper_diagnostic_v1.json').read_text())

    def test_factorial_control_failure_and_low_plain_coverage_preserved(self):
        result=analysis.verify(self.data)
        self.assertEqual(result['verified_rows'],308)
        self.assertEqual(len(result['paired_probabilities']),77)
        cells=result['comparisons'][0]['cells']
        self.assertEqual([cells[w]['attack']['flagged'] for w in ('G1T1','G1T0','G0T1','G0T0')],[75,75,70,1])
        self.assertEqual([cells[w]['clean']['flagged'] for w in ('G1T1','G1T0','G0T1','G0T0')],[1,1,1,0])

    def test_case_and_weight_identity_changes_are_rejected(self):
        for change in ('case','weights'):
            data=copy.deepcopy(self.data)
            if change=='case':data['rows'][0]['prompt']='changed'
            else:data['model']['weights_sha256']='changed'
            with self.assertRaises(ValueError):analysis.verify(data)

    def test_invented_summary_and_invalid_probability_are_rejected(self):
        for change in ('summary','probability'):
            data=copy.deepcopy(self.data)
            if change=='summary':data['comparisons'][0]['cells']['G0T0']['attack']['flagged']=75
            else:data['rows'][0]['injection_probability']=float('inf')
            with self.assertRaises(ValueError):analysis.verify(data)
