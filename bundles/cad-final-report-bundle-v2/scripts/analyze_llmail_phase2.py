"""Reconcile frozen content-only Phase 2 predictions without loading an encoder."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import tarfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from context_pair_v2 import digest
from llmail_thresholds import at_threshold


def require(condition, message):
    if not condition:
        raise ValueError(message)


def analyze(path):
    with tarfile.open(path) as archive:
        members = archive.getmembers()
        require(len(members) == 1 and members[0].name == 'phase2_transfer_result.json'
                and members[0].isfile() and members[0].size < 10_000_000, 'Unexpected archive contents')
        data = json.load(archive.extractfile(members[0]))
    require(data['status'] == 'completed' and data['training_performed'] is False, 'Unexpected run status')
    require(data['script_sha256'] == digest(ROOT/'scripts/evaluate_llmail_phase2.py'), 'Scorer source mismatch')
    require(data['source_revision'] == '1063bdf01ec8762b812d5e06ee768a06faa5a6f7', 'Source revision mismatch')
    reference = json.loads((ROOT/'reports/evidence/llmail_phase2_preflight_20261024/failed_result.json').read_text())
    require(data['files'] == reference['files'], 'Payload hashes mismatch')
    policy_path = ROOT/'reports/evidence/llmail_benign_20261023/threshold_policy.json'
    policy = json.loads(policy_path.read_text())
    require(data['policy_sha256'] == digest(policy_path) and data['metadata_sha256'] == policy['metadata_sha256'], 'Model/policy mismatch')
    protocol = data['protocol']
    require(protocol['task_context_used'] is False and protocol['evaluated_modes'] == ['content_only']
            and protocol['phase2_level_to_original_scenario'] is None, 'Unapproved context inference')
    require(protocol['inspect_hash_first'] == 5000 and protocol['score_maximum'] == 2000
            and protocol['seed'] == 'phase2-transfer-v1', 'Sampling protocol mismatch')
    require(data['embedding_revision'] == '1110a243fdf4706b3f48f1d95db1a4f5529b4d41'
            and data['device'] == 'cuda:0' and data['dtype'] == 'torch.float16', 'Encoder mismatch')
    require(set(data['models']) == {'content_only'}, 'Unexpected evaluated head')
    record = data['models']['content_only']; rows = record['rows']
    require(len(rows) == data['scored_count'] == 2000, 'Scored count mismatch')
    require(len({r['id'] for r in rows}) == len(rows), 'Duplicate prediction ID')
    for row in rows:
        require(re.fullmatch(r'LLMAIL-P2-[0-9a-f]{64}', row['id']) is not None, 'Invalid prediction ID')
        require(row['source_attack_attempt'] in ('True', 'False') and type(row['team_new']) is bool, 'Invalid label/cohort')
        require(row['observed_scenario'] is None and isinstance(row['observed_level'], str), 'Unexpected inferred scenario')
        require(type(row['probability']) in (int, float) and math.isfinite(row['probability']) and 0 <= row['probability'] <= 1, 'Invalid probability')
    keys = [hashlib.sha256(('phase2-transfer-v1:' + r['id']).encode()).hexdigest() for r in rows]
    require(keys == sorted(keys), 'Hash selection order mismatch')
    require(dict(Counter(r['source_attack_attempt'] for r in rows)) == data['scored_labels'], 'Label count mismatch')
    require(sum(r['team_new'] for r in rows) == data['scored_team_new_count'], 'Team cohort mismatch')
    require(data['hash_sample_inspected'] == data['hash_sample_long_excluded'] + data['eligible_short_sample_count'] == 5000, 'Eligibility accounting mismatch')
    cohorts = {'all_text_novel': rows, 'text_and_team_new': [r for r in rows if r['team_new']]}
    require(set(record['cohorts']) == set(cohorts), 'Unexpected cohorts')
    summary = {}
    for name, selected in cohorts.items():
        observed = record['cohorts'][name]
        require(observed['count'] == len(selected), 'Cohort denominator mismatch')
        summary[name] = {'count': len(selected), 'labels': dict(Counter(r['source_attack_attempt'] for r in selected))}
        for label, cutoff in [('original_cutoff', .5), ('validation_selected_cutoff', policy['thresholds']['content_only'])]:
            expected = at_threshold(selected, [r['probability'] for r in selected], cutoff)
            actual = observed[label]
            require(set(actual) == set(expected), 'Metric fields mismatch')
            for key, value in expected.items():
                require(math.isclose(value, actual[key], abs_tol=1e-12, rel_tol=0) if type(value) is float else value == actual[key], 'Metric mismatch: '+name+'/'+label+'/'+key)
            summary[name][label] = expected
    return {'archive_sha256': digest(path), 'cohorts': summary, 'training_performed': False,
            'scope': 'Saved probabilities, counts, frozen hashes and metrics verified. Raw source joins, overlap filtering, team ownership and GPU embeddings are operator-recorded, not independently reproduced. Same-challenge content-only transfer; no downstream prevention measurement.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); result = analyze(args.archive)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
