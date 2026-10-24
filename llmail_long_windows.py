"""Token-preserving offline long-email window embeddings and aggregation."""
import numpy as np


def windows(ids,capacity=254,overlap=32):
    if capacity<1 or not 0<=overlap<capacity:raise ValueError('Invalid window parameters')
    if not ids:raise ValueError('No content tokens')
    output=[];start=0
    while start<len(ids):
        end=min(len(ids),start+capacity)
        output.append((start,end,list(ids[start:end])))
        if end==len(ids):break
        start+=capacity-overlap
    return output


def embed_token_windows(chunks,embedder,batch_size=32):
    import torch
    from torch.nn.functional import normalize
    if not chunks:raise ValueError('No windows to embed')
    if hasattr(embedder,'eval'):embedder.eval()
    result=[]
    for start in range(0,len(chunks),batch_size):
        prepared=[embedder.tokenizer.prepare_for_model(ids,add_special_tokens=True,truncation=False,return_attention_mask=True) for ids in chunks[start:start+batch_size]]
        if any(len(row['input_ids'])>embedder.max_seq_length for row in prepared):raise ValueError('Window exceeds encoder limit')
        features=embedder.tokenizer.pad(prepared,padding=True,return_tensors='pt')
        features={key:value.to(embedder.device) for key,value in features.items()}
        with torch.inference_mode():
            vectors=normalize(embedder(features)['sentence_embedding'],p=2,dim=1)
        result.append(vectors.detach().float().cpu().numpy())
    output=np.concatenate(result,axis=0)
    if not np.isfinite(output).all():raise ValueError('Non-finite window embeddings')
    return output


def aggregate(probabilities):
    p=np.asarray(probabilities,dtype=np.float64)
    if p.ndim!=1 or not len(p) or not np.isfinite(p).all() or np.any((p<0)|(p>1)):raise ValueError('Invalid window probabilities')
    return {'first_window':float(p[0]),'max_window':float(p.max()),'mean_window':float(p.mean())}
