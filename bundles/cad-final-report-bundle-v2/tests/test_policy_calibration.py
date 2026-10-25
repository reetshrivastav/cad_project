import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
import pandas as pd
import app

spec = importlib.util.spec_from_file_location(
    'calibration', Path(__file__).resolve().parents[1] / 'scripts/calibrate_policy_candidates.py')
calibration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calibration)


class CalibrationTests(unittest.TestCase):
    def test_retains_all_scores_and_does_not_forward(self):
        features = [{name: 0 for name in app.FEATURE_COLUMNS} for _ in range(2)]
        for count, row in enumerate(features, 1):
            row['session_repeat_count'] = count
        classifier = Mock()
        classifier.risk_scores.side_effect = [
            (pd.Series([r]), pd.Series(['exhaustion']), pd.DataFrame([{'benign': 1-r, 'exhaustion': r}]))
            for r in (.3, .7)]
        with patch.object(app, '_classifier', classifier), \
             patch.object(app, 'extract_real_features', side_effect=features), \
             patch.object(app, 'call_vllm') as forward:
            rows = calibration.score_candidates(['test'], 2)
        forward.assert_not_called()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['static_or_normal_tier'], 'full')
        self.assertEqual(rows[0]['counterfactual_high_pressure_tier'], 'sandbox')
        self.assertEqual(rows[1]['counterfactual_high_pressure_tier'], 'quarantine')
        self.assertEqual(calibration.select_bands(rows)['sandbox_to_quarantine']['first_id'], 'P01-S02')

    def test_empty_band_is_reported_without_inventing_a_candidate(self):
        bands = calibration.select_bands([{'id': 'P01-S01', 'risk': .99}])
        self.assertEqual(bands['sandbox_to_quarantine'], {'count': 0, 'first_id': None})
