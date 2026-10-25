import importlib.util
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('native_verify', ROOT / 'scripts/verify_native_artifacts.py')
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


class NativeArtifactTests(unittest.TestCase):
    def test_retained_archive_matches_experiment(self):
        result = native.verify()
        self.assertEqual(len(result['verified_artifacts']), 4)
        self.assertTrue(result['metadata_matches'])
        self.assertFalse(result['deserialized_models'])

    def test_directory_corruption_and_metadata_drift_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            model_dir = Path(directory)
            with tarfile.open(native.EVIDENCE / 'cad-lab-native-v1.tar.gz') as handle:
                for member in handle.getmembers():
                    if member.isfile():
                        (model_dir / Path(member.name).name).write_bytes(handle.extractfile(member).read())
            self.assertTrue(native.verify(model_dir=model_dir)['metadata_matches'])
            metadata = model_dir / 'model_metadata.json'
            original = metadata.read_bytes()
            metadata.write_text(json.dumps({'accuracy': 1.0}))
            with self.assertRaisesRegex(ValueError, 'metadata'):
                native.verify(model_dir=model_dir)
            metadata.write_bytes(original)
            (model_dir / 'classifier.joblib').write_bytes(b'corrupted')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                native.verify(model_dir=model_dir)

    def test_altered_archive_rejected_before_opening(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'changed.tar.gz'
            archive.write_bytes(b'not the retained archive')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                native.verify(archive=archive)
