import copy
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from analyze_llmail_phase2 import analyze
FIXTURE = Path(__file__).parent/'fixtures/llmail-phase2-content-v1.tar.gz'


class Phase2ContentTests(unittest.TestCase):
    def test_recorded_metrics_reconcile(self):
        result = analyze(FIXTURE)
        self.assertEqual(result['cohorts']['all_text_novel']['count'], 2000)
        self.assertEqual(result['cohorts']['text_and_team_new']['validation_selected_cutoff']['fp'], 5)

    def test_corrupt_predictions_and_scope_are_rejected(self):
        with tarfile.open(FIXTURE) as archive:
            original = json.load(archive.extractfile('phase2_transfer_result.json'))
        mutations = [lambda d: d['models']['content_only']['rows'][0].update(probability=float('nan')),
                     lambda d: d['models']['content_only']['cohorts']['all_text_novel']['original_cutoff'].update(tp=1729),
                     lambda d: d['protocol'].update(task_context_used=True),
                     lambda d: d.update(metadata_sha256='invalid')]
        for mutate in mutations:
            with self.subTest(mutation=mutate), tempfile.TemporaryDirectory() as directory:
                data = copy.deepcopy(original); mutate(data)
                payload = json.dumps(data).encode(); path = Path(directory)/'test.tar.gz'
                with tarfile.open(path, 'w:gz') as archive:
                    member = tarfile.TarInfo('phase2_transfer_result.json'); member.size = len(payload)
                    archive.addfile(member, io.BytesIO(payload))
                with self.assertRaises(ValueError):
                    analyze(path)
