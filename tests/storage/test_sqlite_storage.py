import os
from phi.storage.agent.sqlite import SqlAgentStorage
from tests.storage.test_base_storage import BaseStorageTest

class TestSqliteStorage(BaseStorageTest):
    def setUp(self):
        self.db_file = "test_db.sqlite"
        self.storage = SqlAgentStorage(table_name="agent_sessions", db_file=self.db_file)
        self.storage.create()

    def tearDown(self):
        if os.path.exists(self.db_file):
            os.remove(self.db_file)
