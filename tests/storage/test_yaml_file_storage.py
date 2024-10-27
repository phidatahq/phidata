import shutil
from pathlib import Path
from phi.storage.agent.yaml_file_storage import YamlFileStorage
from tests.storage.test_base_storage import BaseStorageTest

class TestYamlFileStorage(BaseStorageTest):
    def setUp(self):
        self.test_dir = Path("test_storage")
        self.storage = YamlFileStorage(path=self.test_dir)
        self.storage.create()

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
