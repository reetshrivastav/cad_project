import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('heldout_prepare', ROOT / 'scripts/prepare_heldout_candidates.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class HeldoutPreparationTests(unittest.TestCase):
    def test_native_training_reconstruction_and_frozen_candidates(self):
        audit, candidates = prepare.build(ROOT)
        self.assertEqual(audit['reconstructed_training_rows'], dict(benign=2700, injection=994, exhaustion=635))
        self.assertEqual(audit['advbench_source_rows_held_out'], 0)
        self.assertEqual(len(candidates), 200)
        retained = [json.loads(line) for line in (ROOT / 'reports/evidence/heldout_preparation_20261022/candidates.jsonl').read_text().splitlines()]
        self.assertEqual(candidates, retained)
        self.assertTrue(all(not r['label'] and not r['reviewer'] for r in candidates))
        self.assertFalse(audit['metrics_computed'])

    def test_normalization_and_near_duplicates_are_excluded(self):
        self.assertEqual(prepare.normalize('Ａlpha, BETA!'), 'alpha beta')
        items = [{'instruction': 'unused'}] * 800 + [
            {'instruction': 'ALPHA, BETA'},
            {'instruction': 'alpha beta gamma delta epsilon zeta'},
            {'instruction': 'A distinct question about astronomy'}]
        forbidden = {'alpha beta', 'alpha beta gamma delta epsilon'}
        rows, exclusions = prepare.select_candidates(items, forbidden, 1)
        self.assertEqual(rows[0]['source_index_zero_based'], 802)
        self.assertEqual(exclusions, {'normalized_exact_overlap': 1, 'token_set_jaccard_ge_0_8': 1})

    def test_dataset_checksum_mismatch_stops_reconstruction(self):
        metadata = json.loads((ROOT / 'reports/evidence/native_burst_20261018/lab_native_v1_metadata.json').read_text())
        metadata = copy.deepcopy(metadata)
        metadata['dataset_files']['alpaca_sample.json'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            prepare.reconstruct_training(ROOT, metadata)
