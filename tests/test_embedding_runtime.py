import unittest
from unittest.mock import Mock
import numpy as np
import torch
from embedding_runtime import encode_prompt


class EmbeddingRuntimeTests(unittest.TestCase):
    def test_direct_normalizes_and_disables_gradients(self):
        class Model:
            training = False
            device = torch.device('cpu')
            def tokenize(self, texts):
                self.texts = texts
                return {'input_ids': torch.tensor([[1, 2]])}
            def __call__(self, features):
                assert torch.is_inference_mode_enabled()
                return {'sentence_embedding': torch.tensor([[3., 4.]])}
        model = Model()
        np.testing.assert_allclose(encode_prompt(model, 'hello', 'direct'), [[.6, .8]])
        self.assertEqual(model.texts, ['hello'])

    def test_default_uses_existing_encode(self):
        model = Mock()
        encode_prompt(model, 'hello')
        model.encode.assert_called_once_with(['hello'], convert_to_numpy=True,
                                            normalize_embeddings=True, show_progress_bar=False)

    def test_invalid_or_training_mode_rejected(self):
        with self.assertRaises(ValueError):
            encode_prompt(Mock(), 'hello', 'invalid')
        with self.assertRaises(RuntimeError):
            encode_prompt(Mock(training=True), 'hello', 'direct')
