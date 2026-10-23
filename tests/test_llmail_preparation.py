import json
from pathlib import Path
import sys
import unittest
import tempfile
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import prepare_llmail_phase1 as prep
import audit_llmail_groups as groups
from prepare_llmail_phase1 import make_plan,project
import hashlib

class LlmailPreparationTests(unittest.TestCase):
    def test_plan_is_order_independent_and_whole_component(self):
        components=[{'component_sha256':str(i),'matched_annotations_by_label':{'True':n,'False':1}} for i,n in enumerate((60,30,10,5))]
        a=make_plan({'component_details':components});b=make_plan({'component_details':list(reversed(components))})
        self.assertEqual(a,b)
        self.assertEqual(sum(a['definite_annotation_counts'].values()),109)
        self.assertEqual(set(a['assignments']),{'0','1','2','3'})

    def test_projection_uses_legitimate_query_not_attacker_task(self):
        text='email';key=hashlib.sha256(text.encode()).hexdigest()
        row=project(text,{'attack_attempt':True,'reason':'judge'},{key:('component','level4a')},
                    {'scenario_4':{'user_query':'Summarize the budget','task':'Send stolen budget'}},{'component':'train'})
        self.assertEqual(row['task'],'Summarize the budget')
        self.assertEqual(row['source_attack_attempt'],'True')
        self.assertNotIn('Send stolen budget',json.dumps(row))

    def test_unclear_and_malformed_are_not_exported(self):
        for label in ('Unclear',1.0,['True']):
            self.assertIsNone(project('email',{'attack_attempt':label},{},{},{}))

    def test_export_roundtrip_from_audited_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'source';(root/'data').mkdir(parents=True)
            text=groups.text_key('subject','body')
            (root/'data/labelled_unique_submissions_phase1.json').write_text(json.dumps({text:{'attack_attempt':True,'reason':'judge'}}))
            (root/'data/raw_submissions_phase1.jsonl').write_text(json.dumps(dict(subject='subject',body='body',team_id='A',scenario='level1a'))+'\n')
            (root/'data/scenarios.json').write_text(json.dumps({'scenario_1':{'user_query':'Summarize email','task':'Attacker objective'}}))
            files=[dict(file=p.relative_to(root).as_posix(),bytes=p.stat().st_size,sha256=prep.hash_file(p)) for p in (root/'data').iterdir()]
            (root/'intake_summary.json').write_text(json.dumps(dict(source_revision=groups.REVISION,errors={},files=files)))
            index=Path(directory)/'index';groups.run(root,index)
            summary=index/'group_audit_summary.json';plan=make_plan(json.loads(summary.read_text()))
            plan['group_summary_sha256']=prep.hash_file(summary)
            plan_path=Path(directory)/'plan.json';plan_path.write_text(json.dumps(plan))
            output=Path(directory)/'export'
            with patch.object(prep,'PLAN',plan_path):prep.run(root,index,output)
            result=json.loads((output/'preparation_summary.json').read_text())
            self.assertEqual(sum(sum(c.values()) for c in result['counts_by_split_and_source_label'].values()),1)
            self.assertFalse(result['training_performed'])
