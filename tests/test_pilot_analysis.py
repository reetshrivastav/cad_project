import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    'analysis', Path(__file__).resolve().parents[1] / 'scripts/analyze_gpu_pilot.py')
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


class AnalysisTests(unittest.TestCase):
    def test_missing_counter_not_zero(self):
        self.assertIsNone(analysis.counter_delta([{}, {}], 'tokens'))
        self.assertIsNone(analysis.counter_delta([
            {'metrics': [{'name': 'tokens', 'value': 2}]}, {}], 'tokens'))

    def test_counter_reset_is_rejected(self):
        samples = [{'metrics': [{'name': 'tokens', 'value': v}]} for v in [3, 1]]
        with self.assertRaises(ValueError):
            analysis.counter_delta(samples, 'tokens')

    def test_labeled_counter_series_are_summed(self):
        samples = [{'metrics': [{'name': 'tokens', 'value': v},
                                {'name': 'tokens', 'value': 1}]} for v in [3, 8]]
        self.assertEqual(analysis.counter_delta(samples, 'tokens'), 5)
