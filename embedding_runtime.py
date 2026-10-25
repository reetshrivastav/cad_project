"""Explicit, opt-in single-request SentenceTransformer inference path."""
import torch


def encode_prompt(model, prompt, mode='encode'):
    if mode == 'encode':
        return model.encode([prompt], convert_to_numpy=True,
                            normalize_embeddings=True, show_progress_bar=False)
    if mode != 'direct':
        raise ValueError('Embedding mode must be encode or direct')
    if model.training:
        raise RuntimeError('Direct embedding requires an evaluation-mode model')
    features = model.tokenize([prompt])
    features = {key: value.to(model.device) if isinstance(value, torch.Tensor) else value
                for key, value in features.items()}
    with torch.inference_mode():
        result = model(features)['sentence_embedding']
        result = torch.nn.functional.normalize(result, p=2, dim=1)
    return result.cpu().numpy()
