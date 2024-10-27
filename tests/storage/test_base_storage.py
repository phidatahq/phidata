import unittest
from phi.agent import AgentSession

class BaseStorageTest(unittest.TestCase):
    def setUp(self):
        if self.storage is None:
            self.skipTest("Storage not initialized in subclass")

    def test_create_and_read_session(self):
        session = AgentSession(session_id="test_session", agent_id="agent_1", user_id="user_1")
        self.storage.upsert(session)
        read_session = self.storage.read("test_session")
        self.assertIsNotNone(read_session)
        self.assertEqual(read_session.session_id, "test_session")

    def test_get_all_session_ids(self):
        session1 = AgentSession(session_id="session_1", agent_id="agent_1", user_id="user_1")
        session2 = AgentSession(session_id="session_2", agent_id="agent_1", user_id="user_1")
        self.storage.upsert(session1)
        self.storage.upsert(session2)
        session_ids = self.storage.get_all_session_ids()
        self.assertIn("session_1", session_ids)
        self.assertIn("session_2", session_ids)

    def test_delete_session(self):
        session = AgentSession(session_id="test_session", agent_id="agent_1", user_id="user_1")
        self.storage.upsert(session)
        self.storage.delete_session("test_session")
        read_session = self.storage.read("test_session")
        self.assertIsNone(read_session)
