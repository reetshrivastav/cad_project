import sys
from pathlib import Path
import unittest
import numpy as np
sys.path[:0]=[str(Path(__file__).resolve().parents[1])]
from llmail_long_windows import windows,aggregate,embed_token_windows

class LongWindowTests(unittest.TestCase):
    def test_every_token_is_covered_without_decoding_or_truncation(self):
        for n in (1,254,255,476,900,12912):
            ids=list(range(n));parts=windows(ids);coverage=set()
            for a,b,chunk in parts:
                self.assertEqual(chunk,ids[a:b]);self.assertLessEqual(len(chunk),254);coverage.update(range(a,b))
            self.assertEqual(coverage,set(range(n)))
            self.assertEqual(parts[0][0],0);self.assertEqual(parts[-1][1],n)
    def test_invalid_or_empty_windows_rejected(self):
        for params in [(0,0),(254,254),(254,-1)]:
            with self.assertRaises(ValueError):windows([1],*params)
        with self.assertRaises(ValueError):windows([])
    def test_aggregation_preserves_tail_signal_and_dilution(self):
        result=aggregate([.01,.01,.99]);self.assertEqual(result['max_window'],.99)
        self.assertEqual(result['first_window'],.01);self.assertLess(result['mean_window'],.5)
        with self.assertRaises(ValueError):aggregate([float('nan')])
    def test_direct_token_embedding_preserves_ids(self):
        import torch
        seen=[]
        class Tokenizer:
            def prepare_for_model(self,ids,**kwargs):
                seen.append(list(ids));return {'input_ids':[101]+list(ids)+[102],'attention_mask':[1]*(len(ids)+2)}
            def pad(self,rows,**kwargs):
                n=max(len(r['input_ids']) for r in rows)
                return {k:torch.tensor([r[k]+[0]*(n-len(r[k])) for r in rows]) for k in rows[0]}
        class Embedder:
            tokenizer=Tokenizer();device='cpu';max_seq_length=256
            def __call__(self,features):return {'sentence_embedding':torch.stack([features['input_ids'].sum(1),features['attention_mask'].sum(1)],dim=1).float()}
        chunks=[[200,300],[999]];vectors=embed_token_windows(chunks,Embedder())
        self.assertEqual(seen,chunks);self.assertEqual(vectors.shape,(2,2))
        np.testing.assert_allclose(np.linalg.norm(vectors,axis=1),1,atol=1e-6)
