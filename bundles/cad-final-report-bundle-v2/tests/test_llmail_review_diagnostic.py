import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from llmail_thresholds import at_threshold

class ReviewDiagnosticTests(unittest.TestCase):
    def test_stored_diagnostic_probabilities_reproduce_confusions(self):
        path=ROOT/'reports/evidence/llmail_review_comparison_20261023/verified_diagnostic.json'
        result=json.loads(path.read_text())
        for mode,record in result['models'].items():
            selected=[r for r in record['reviewed_probabilities'] if r['review_label']!='unclear']
            self.assertEqual(len(selected),66)
            rows=[dict(source_attack_attempt='True' if r['review_label']=='injection' else 'False') for r in selected]
            for metrics in record['metrics'].values():
                calculated=at_threshold(rows,[r['probability'] for r in selected],metrics['threshold'])
                self.assertEqual([calculated[k] for k in ('tp','fn','fp','tn')],[metrics[k] for k in ('tp','fn','fp','tn')])
        pair=result['models']['pair']['metrics']['original_cutoff']
        self.assertEqual((pair['tp'],pair['fp'],pair['tn']),(42,19,5))

    def test_review_disagreements_do_not_erase_original_reserved_findings(self):
        root=ROOT/'reports/evidence'
        comparison=json.loads((root/'llmail_review_comparison_20261023/llmail_ai_review_comparison_v1.json').read_text())
        self.assertEqual(comparison['source_label_vs_review']['False/injection'],11)
        self.assertFalse(comparison['training_performed'])
        original=json.loads((root/'llmail_reserved_20261023/verified_summary.json').read_text())
        self.assertEqual(original['models']['pair']['validation_selected_cutoff']['fp'],165)
        self.assertEqual(original['models']['pair']['validation_selected_cutoff']['fn'],5101)
