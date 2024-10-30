import unittest
from unittest.mock import patch, MagicMock
from couchbase.exceptions import CouchbaseException
from phi.vectordb.couchbase.couchbase import CouchbaseVectorDb
from phi.document import Document

class TestCouchbaseVectorDb(unittest.TestCase):

    @patch('phi.vectordb.couchbase.couchbase.Cluster')
    def setUp(self, MockCluster):
        self.mock_cluster = MockCluster.return_value
        self.mock_bucket = self.mock_cluster.bucket.return_value
        self.mock_collection = self.mock_bucket.collection.return_value

        self.vector_db = CouchbaseVectorDb(
            bucket_name="test_bucket",
            collection_name="test_collection",
            username="test_user",
            password="test_password",
            host="localhost"
        )

    def test_create_collection(self):
        self.vector_db.create()
        self.mock_bucket.collections().create_scope.assert_called_with("test_collection")

    def test_doc_exists(self):
        document = Document(content="test content")
        doc_id = document.id
        self.mock_collection.get.return_value = MagicMock()
        self.assertTrue(self.vector_db.doc_exists(document))
        self.mock_collection.get.assert_called_with(doc_id)

    def test_doc_not_exists(self):
        document = Document(content="test content")
        doc_id = document.id
        self.mock_collection.get.side_effect = CouchbaseException
        self.assertFalse(self.vector_db.doc_exists(document))
        self.mock_collection.get.assert_called_with(doc_id)

    def test_name_exists(self):
        self.mock_cluster.query.return_value.rows.return_value = [MagicMock()]
        self.assertTrue(self.vector_db.name_exists("test_name"))
        self.mock_cluster.query.assert_called_with(
            f"SELECT META().id FROM `test_bucket`.`test_collection` WHERE name = $1", "test_name"
        )

    def test_name_not_exists(self):
        self.mock_cluster.query.return_value.rows.return_value = []
        self.assertFalse(self.vector_db.name_exists("test_name"))
        self.mock_cluster.query.assert_called_with(
            f"SELECT META().id FROM `test_bucket`.`test_collection` WHERE name = $1", "test_name"
        )

    def test_insert_document(self):
        document = Document(content="test content")
        self.vector_db.insert([document])
        doc_id = document.id
        self.mock_collection.upsert.assert_called_with(doc_id, {
            "name": document.name,
            "meta_data": document.meta_data,
            "content": document.content,
            "embedding": document.embedding,
            "usage": document.usage,
        })

    def test_upsert_document(self):
        document = Document(content="test content")
        self.vector_db.upsert([document])
        doc_id = document.id
        self.mock_collection.upsert.assert_called_with(doc_id, {
            "name": document.name,
            "meta_data": document.meta_data,
            "content": document.content,
            "embedding": document.embedding,
            "usage": document.usage,
        })

    def test_search_documents(self):
        document = Document(content="test content")
        self.mock_cluster.query.return_value.rows.return_value = [{
            "id": document.id,
            "name": document.name,
            "meta_data": document.meta_data,
            "content": document.content,
            "embedding": document.embedding,
            "usage": document.usage,
        }]
        results = self.vector_db.search("test query")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].content, document.content)

    def test_drop_collection(self):
        self.vector_db.drop()
        self.mock_bucket.collections().drop_scope.assert_called_with("test_collection")

    def test_collection_exists(self):
        self.mock_bucket.collections().get_scope.return_value = MagicMock()
        self.assertTrue(self.vector_db.exists())
        self.mock_bucket.collections().get_scope.assert_called_with("test_collection")

    def test_collection_not_exists(self):
        self.mock_bucket.collections().get_scope.side_effect = CouchbaseException
        self.assertFalse(self.vector_db.exists())
        self.mock_bucket.collections().get_scope.assert_called_with("test_collection")

    def test_delete_documents(self):
        self.vector_db.delete()
        self.mock_bucket.collections().drop_scope.assert_called_with("test_collection")

if __name__ == '__main__':
    unittest.main()
