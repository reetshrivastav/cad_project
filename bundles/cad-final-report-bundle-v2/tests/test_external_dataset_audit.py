import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('dataset_audit',ROOT/'scripts/audit_external_datasets.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)

class DatasetAuditTests(unittest.TestCase):
    def test_hf_pins_card_and_listing_without_fetching_payloads(self):
        revision='a'*40
        info={'sha':revision,'cardData':{'license':'test-license'},'siblings':[{'rfilename':'data/train.parquet'}]}
        urls=[]
        def fetch(url):
            urls.append(url)
            return b'# Card' if url.endswith('README.md') else json.dumps(info).encode()
        with tempfile.TemporaryDirectory() as directory,patch.object(audit,'fetch',side_effect=fetch):
            result=audit.audit_hf(Path(directory))
        self.assertFalse(result['payloads_downloaded'])
        self.assertTrue(any('/revision/'+revision in url for url in urls))
        self.assertTrue(any('/raw/'+revision+'/README.md' in url for url in urls))
        self.assertFalse(any(url.endswith('.parquet') for url in urls))

    def test_changed_revision_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(audit,'fetch',side_effect=[json.dumps({'sha':'a'*40}).encode(),json.dumps({'sha':'b'*40}).encode()]):
            with self.assertRaisesRegex(ValueError,'revision changed'):audit.audit_hf(Path(directory))
