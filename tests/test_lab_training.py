"""Exercise versioned exports with a tiny dataset and mocked embedding work."""
import json
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import numpy as np
import train_on_datasets as training


class LabTrainingTests(unittest.TestCase):
    def test_refuses_nonempty_output_before_loading_models(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'keep.txt').write_text('preserve')
            with patch('sys.argv', ['train', '--output-dir', directory]), \
                 patch.object(training, 'SentenceTransformer') as embed, \
                 contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                training.main()
            embed.assert_not_called()
            self.assertEqual(Path(directory, 'keep.txt').read_text(), 'preserve')

    def test_versioned_export_and_runtime_metadata(self):
        embedder = Mock()
        embedder.encode.return_value = np.ones((len(training.REFERENCE_JAILBREAKS), 384), dtype=np.float32)
        features = {name: 1.0 for name in training.FEATURE_COLUMNS}
        original_output = training.MODELS_DIR
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'new-model'
            try:
                with patch('sys.argv', ['train', '--output-dir', str(target)]), \
                     patch.object(training, 'SentenceTransformer', return_value=embedder), \
                     patch.object(training.tiktoken, 'get_encoding'), \
                     patch.object(training, 'download_advbench', return_value=['attack']), \
                     patch.object(training, 'download_benign_prompts', return_value=['benign']), \
                     patch.object(training, 'generate_exhaustion_prompts', return_value=[('demand', 1, 100)]), \
                     patch.object(training, 'extract_features_for_prompt', side_effect=lambda *a, **k: dict(features)), \
                     patch.object(training.log, 'disabled', True):
                    training.main()
                meta = json.loads((target / 'model_metadata.json').read_text())
                self.assertEqual(meta['accuracy_scope'], 'training_set_resubstitution_not_held_out')
                self.assertIn('python', meta['runtime'])
                self.assertEqual(set(meta['artifact_sha256']), {
                    'classifier.joblib', 'tfidf.joblib', 'ref_embeddings.npy', 'reference_jailbreaks.json'})
            finally:
                training.MODELS_DIR = original_output
