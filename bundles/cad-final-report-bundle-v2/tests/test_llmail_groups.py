import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import audit_llmail_groups as groups

class LlmailGroupsTests(unittest.TestCase):
    def test_literal_labels_only(self):
        self.assertEqual(groups.label_class('Unclear'),'Unclear')
        self.assertEqual(groups.label_class(True),'True')
        self.assertEqual(groups.label_class(False),'False')
        for value in (1.0,['False','True'],None):self.assertEqual(groups.label_class(value),'malformed')

    def test_join_preserves_cross_team_components_and_unmatched(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'source';(root/'data').mkdir(parents=True);out=Path(directory)/'output'
            text=groups.text_key('Hello','body')
            annotations={text:{'attack_attempt':True,'reason':'judge'},'unmatched':{'attack_attempt':'Unclear','reason':'judge'}}
            raw=[dict(subject='Hello',body='body',team_id=t,scenario='level1a') for t in ('A','B')]
            raw.append(dict(subject='Other',body='clean',team_id='C',scenario='level2b'))
            (root/'data/labelled_unique_submissions_phase1.json').write_text(json.dumps(annotations))
            (root/'data/raw_submissions_phase1.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in raw))
            files=[dict(file=p.relative_to(root).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in (root/'data').iterdir()]
            (root/'intake_summary.json').write_text(json.dumps(dict(source_revision=groups.REVISION,errors={},files=files)))
            groups.run(root,out);summary=json.loads((out/'group_audit_summary.json').read_text())
            self.assertEqual(summary['matched_raw_rows'],2)
            self.assertEqual(summary['unmatched_annotations'],1)
            self.assertEqual(summary['component_team_sizes_descending'],[2,1])
            self.assertFalse(summary['training_performed'])
            self.assertEqual(summary['source_label_types'],{'bool':1,'str':1})
            self.assertEqual(sum(c['matched_annotations_by_label'].get('True',0) for c in summary['component_details']),1)

    def test_numeric_truthiness_does_not_create_positive_labels(self):
        for value in (1,1.0,0,0.0,'true','false','1','',[],{}):
            self.assertEqual(groups.label_class(value),'malformed')
