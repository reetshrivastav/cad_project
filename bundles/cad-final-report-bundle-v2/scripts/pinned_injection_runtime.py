"""Pinned detector loading for follow-up diagnostics, not gateway integration."""
import time
from pathlib import Path

from evaluate_injection_candidate import MODEL_ID,MODEL_REVISION,injection_label_index,file_sha256


def load_detector(local_files_only=True):
    import torch
    from transformers import AutoTokenizer,AutoModelForSequenceClassification
    from huggingface_hub import hf_hub_download
    if not torch.cuda.is_available():raise ValueError('CUDA required; no CPU fallback')
    torch.manual_seed(0)
    torch.cuda.reset_peak_memory_stats()
    kwargs={'revision':MODEL_REVISION,'local_files_only':local_files_only}
    tokenizer=AutoTokenizer.from_pretrained(MODEL_ID,trust_remote_code=False,**kwargs)
    model=AutoModelForSequenceClassification.from_pretrained(MODEL_ID,trust_remote_code=False,
            use_safetensors=True,torch_dtype=torch.float16,**kwargs).to('cuda').eval()
    index=injection_label_index(model.config.id2label)
    if getattr(model.config,'_commit_hash',MODEL_REVISION)!=MODEL_REVISION:raise ValueError('Model revision mismatch')
    if str(next(model.parameters()).dtype)!='torch.float16':raise ValueError('Expected FP16')
    weights=Path(hf_hub_download(MODEL_ID,'model.safetensors',**kwargs))
    card=Path(hf_hub_download(MODEL_ID,'README.md',**kwargs))
    limit=min(512,int(tokenizer.model_max_length),int(model.config.max_position_embeddings))
    metadata={'model_id':MODEL_ID,'model_revision':MODEL_REVISION,'weights_sha256':file_sha256(weights),
              'weights_bytes':weights.stat().st_size,'model_card_sha256':file_sha256(card),
              'device':str(next(model.parameters()).device),'dtype':str(next(model.parameters()).dtype),
              'max_input_tokens':limit,'id2label':model.config.id2label}

    def score(prompt):
        torch.cuda.synchronize();started=time.perf_counter()
        encoded=tokenizer(prompt,return_tensors='pt',truncation=False,return_token_type_ids=False)
        length=encoded['input_ids'].shape[1]
        if length>limit:raise ValueError(f'{length} tokens exceeds {limit}; no truncation')
        with torch.inference_mode():
            logits=model(**{k:v.to('cuda') for k,v in encoded.items()}).logits
            if tuple(logits.shape)!=(1,2):raise ValueError('Unexpected logits shape')
            probability=torch.softmax(logits.float(),dim=-1)[0,index].item()
        torch.cuda.synchronize()
        return {'injection_probability':probability,'detector_input_tokens':length,
                'tokenization_and_inference_ms':(time.perf_counter()-started)*1000}
    return score,metadata
