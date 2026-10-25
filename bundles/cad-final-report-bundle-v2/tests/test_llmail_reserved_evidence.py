import csv
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from analyze_llmail_reserved import analyze
from export_llmail_label_review import choose,export,FIELDS
ARCHIVE=ROOT/'reports/evidence/llmail_reserved_20261023/llmail-reserved-short-v1.tar.gz'

class ReservedEvidenceTests(unittest.TestCase):
    def test_reserved_metrics_reconcile(self):
        result=analyze(ARCHIVE)
        self.assertEqual(result['models']['pair']['validation_selected_cutoff']['fp'],165)
        self.assertEqual(result['models']['pair']['validation_selected_cutoff']['fn'],5101)

    def test_changed_count_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'changed.tar.gz'
            with tarfile.open(ARCHIVE) as archive:result=json.load(archive.extractfile('llmail_reserved_short_v1.json'))
            result['models']['pair']['original_cutoff']['fp']=0
            data=json.dumps(result).encode();member=tarfile.TarInfo('llmail_reserved_short_v1.json');member.size=len(data)
            with tarfile.open(target,'w:gz') as archive:archive.addfile(member,io.BytesIO(data))
            with self.assertRaises(ValueError):analyze(target)

    def test_blinded_export_is_deterministic_and_development_only(self):
        rows=[dict(id=str(i),split='validation',source_attack_attempt='False' if i<40 else 'True',source_reason='judge',task='query',untrusted_content='email '+str(i),component_sha256='g') for i in range(100)]
        self.assertEqual(choose(rows),choose(list(reversed(rows))))
        with tempfile.TemporaryDirectory() as directory:
            summary=export(rows,Path(directory));self.assertEqual(summary['selected'],80)
            with (Path(directory)/'llmail-label-review-blind.csv').open() as handle:review=list(csv.DictReader(handle))
            self.assertEqual(set(review[0]),set(FIELDS));self.assertTrue(all(r['label']==r['reviewer']==r['notes']=='' for r in review))
        rows[0]['split']='test'
        with self.assertRaises(ValueError):choose(rows)
