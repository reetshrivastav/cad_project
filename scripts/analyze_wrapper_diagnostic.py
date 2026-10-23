"""Verify paired wrapper outcomes offline without loading model weights."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from evaluate_wrapper_diagnostic import load_cases,summarize
from evaluate_injection_candidate import file_sha256,THRESHOLDS,MODEL_ID,MODEL_REVISION,injection_label_index


def verify(data):
    audit,cases=load_cases()
    prior_path=ROOT/'reports/evidence/injection_candidate_scoring_20261023/injection_candidate_shadow_v1.json'
    prior=json.loads(prior_path.read_text())
    expected={'cases_sha256':audit['cases_sha256'],'previous_result_sha256':file_sha256(prior_path),
              'script_sha256':file_sha256(ROOT/'scripts/evaluate_wrapper_diagnostic.py'),
              'runtime_script_sha256':file_sha256(ROOT/'scripts/pinned_injection_runtime.py')}
    if any(data.get(k)!=v for k,v in expected.items()):raise ValueError('Corpus/reference/script checksum mismatch')
    model=data['model']
    if model['model_id']!=MODEL_ID or model['model_revision']!=MODEL_REVISION:raise ValueError('Model identity mismatch')
    if model['weights_sha256']!=prior['weights_sha256'] or model['model_card_sha256']!=prior['model_card_sha256']:
        raise ValueError('Recorded cached model artifacts differ from prior run')
    injection_label_index(model['id2label'])
    if not model['device'].startswith('cuda') or model['dtype']!='torch.float16':raise ValueError('Expected CUDA/FP16 run')
    rows=data['rows']
    if len(rows)!=len(cases) or len({r['id'] for r in rows})!=len(cases):raise ValueError('Missing/duplicate cases')
    by_id={r['id']:r for r in rows}
    for original in cases:
        row=by_id.get(original['id'],{})
        if any(row.get(k)!=v for k,v in original.items()):raise ValueError('Frozen case changed')
        if 'error' in row:continue
        p=row['injection_probability']
        if not math.isfinite(p) or not 0<=p<=1:raise ValueError('Invalid probability')
        if not 0<row['detector_input_tokens']<=model['max_input_tokens']:raise ValueError('Invalid input length')
        elapsed=row['tokenization_and_inference_ms']
        if not math.isfinite(elapsed) or elapsed<0:raise ValueError('Invalid timing')
    comparisons=[summarize(rows,t) for t in THRESHOLDS]
    if comparisons!=data['comparisons'] or data['total_errors']!=sum('error' in r for r in rows):
        raise ValueError('Comparisons/errors differ from rows')
    controls=[{k:r[k] for k in ('id','wrapper','group','injection_probability','error') if k in r}
              for r in rows if r['group']!='attack']
    paired=[]
    for source_id in sorted({r['source_id'] for r in rows}):
        pair={'source_id':source_id}
        for wrapper in ('G1T1','G1T0','G0T1','G0T0'):
            row=next(r for r in rows if r['source_id']==source_id and r['wrapper']==wrapper)
            pair[wrapper]=row.get('injection_probability')
        paired.append(pair)
    return {'verified_rows':len(rows),'comparisons':comparisons,'controls':controls,'paired_probabilities':paired,
            'limits':'Matched development diagnostic; wrapper sensitivity on fixed memo, not deployed false-positive rates or downstream attack success.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    if args.output_dir.exists():parser.error('output directory exists; choose a fresh path')
    data=json.loads(args.input.read_text());result=verify(data)
    args.output_dir.mkdir(parents=True)
    (args.output_dir/'verified_summary.json').write_text(json.dumps(result,indent=2)+'\n')
    with (args.output_dir/'paired_probabilities.csv').open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=['source_id','G1T1','G1T0','G0T1','G0T0'])
        writer.writeheader();writer.writerows(result['paired_probabilities'])
    with (args.output_dir/'all_outcomes.csv').open('w',newline='') as handle:
        fields=['id','wrapper','group','category','source_id','insertion','prompt','injection_probability','detector_input_tokens','tokenization_and_inference_ms','error']
        writer=csv.DictWriter(handle,fieldnames=fields,extrasaction='ignore')
        writer.writeheader();writer.writerows(data['rows'])
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
    labels=['Guard + tags','Guard only','Tags only','Neither']
    wrappers=['G1T1','G1T0','G0T1','G0T0']
    primary=result['comparisons'][0]['cells']
    for offset,group,color in [(-.2,'clean','#bd6249'),(0,'benign_added','#dfb15c'),(.2,'attack','#658895')]:
        values=[100*primary[w][group]['flagged_fraction_of_scored'] for w in wrappers]
        axes[0].bar([i+offset for i in range(4)],values,width=.2,label=group,color=color)
    axes[0].set_xticks(range(4),labels,rotation=15)
    axes[0].set(ylabel='Flagged (%)',ylim=(0,120),title='Primary cutoff >0.92')
    axes[0].legend(fontsize=8,ncol=3,loc='upper left')
    for group,marker,color in [('clean','o','#bd6249'),('benign_added','s','#dfb15c')]:
        controls=[next(r for r in result['controls'] if r['wrapper']==w and r['group']==group)['injection_probability'] for w in wrappers]
        axes[1].plot(range(4),controls,marker=marker,color=color,label=group)
    axes[1].axhline(.92,linestyle='--',color='gray',label='0.92 cutoff')
    axes[1].set_xticks(range(4),labels,rotation=15)
    axes[1].set(ylabel='Candidate injection probability',ylim=(-.05,1.05),title='Harmless controls; one of each per cell')
    axes[1].legend(fontsize=8,loc='lower left')
    fig.suptitle('Pinned candidate: guard/tag sensitivity on matched development cases\n75 attack variants and two harmless controls per cell; no LLM execution',fontsize=11)
    for extension in ('png','svg'):fig.savefig(args.output_dir/f'wrapper_sensitivity.{extension}',dpi=200)
    plt.close(fig)
    print(json.dumps({'verified_rows':result['verified_rows'],'primary':result['comparisons'][0]},indent=2))


if __name__=='__main__':main()
