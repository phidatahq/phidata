import shutil
from pathlib import Path
from phi.storage.agent.json_file_storage import JsonFileStorage
from tests.storage.test_base_storage import BaseStorageTest

class TestJsonFileStorage(BaseStorageTest):
    def setUp(self):
        self.test_dir = Path("test_storage")
        self.storage = JsonFileStorage(path=self.test_dir / "storage.json")
        self.storage.create()

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
