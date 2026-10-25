import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import evaluate_wrapper_diagnostic as evaluation
import prepare_wrapper_diagnostic as preparation
from evaluate_bipia_candidates import load_candidates


class WrapperDiagnosticTests(unittest.TestCase):
    def test_factorial_counts_and_frozen_source_reproduction(self):
        audit,rows=evaluation.load_cases()
        self.assertEqual(audit['case_count'],308)
        self.assertEqual(len({r['id'] for r in rows}),308)
        for wrapper in ('G1T1','G1T0','G0T1','G0T0'):
            self.assertEqual(sum(r['wrapper']==wrapper and r['group']=='attack' for r in rows),75)
            self.assertEqual(sum(r['wrapper']==wrapper and r['group']=='clean' for r in rows),1)
            self.assertEqual(sum(r['wrapper']==wrapper and r['group']=='benign_added' for r in rows),1)

    def test_original_guard_tag_cell_matches_prior_prompts(self):
        _,source=load_candidates()
        _,rows=evaluation.load_cases()
        by_source={r['source_id']:r for r in rows if r['wrapper']=='G1T1'}
        self.assertEqual(by_source['CLEAN']['prompt'],source[0]['prompt'])
        for original in source[1:]:
            self.assertEqual(by_source[original['id']]['prompt'],original['prompt'])

    def test_factor_interventions_do_not_change_memo_or_insertion(self):
        payload='A fixed example insertion.'
        with_both=preparation.render(True,True,payload)
        self.assertEqual(with_both.replace(preparation.GUARD,''),preparation.render(False,True,payload))
        self.assertEqual(with_both.replace('<untrusted_memo>\n','').replace('\n</untrusted_memo>',''),
                         preparation.render(True,False,payload))

    def test_clean_failures_and_attack_errors_stay_separate(self):
        rows=[{'wrapper':'G1T1','group':'clean','injection_probability':.99},
              {'wrapper':'G1T1','group':'attack','error':'failure'}]
        result=evaluation.summarize(rows,.92)['cells']['G1T1']
        self.assertEqual(result['clean']['flagged'],1)
        self.assertEqual(result['attack']['errors'],1)
        self.assertIsNone(result['attack']['flagged_fraction_of_scored'])
