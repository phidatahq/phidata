import unittest

class IndexTests(unittest.TestCase):

    def _getTargetClass(self):
        from pkginfo.index import Index
        return Index

    def _makeOne(self):
        return self._getTargetClass()()

    def test_empty(self):
        index = self._makeOne()
        self.assertEqual(len(index), 0)
        self.assertEqual(len(index.keys()), 0)
        self.assertEqual(len(index.values()), 0)
        self.assertEqual(len(index.items()), 0)

    def _makeDummy(self):
        from pkginfo.distribution import Distribution
        class DummyDistribution(Distribution):
            name = 'dummy'
            version = '1.0'

        return DummyDistribution()

    def test___getitem___miss(self):
        index = self._makeOne()
        self.assertRaises(KeyError, index.__getitem__, 'nonesuch')

    def test___setitem___value_not_dist(self):
        class NotDistribution:
            name = 'dummy'
            version = '1.0'
        dummy = NotDistribution()
        index = self._makeOne()
        self.assertRaises(ValueError, index.__setitem__, 'dummy-1.0', dummy)

    def test___setitem___bad_key(self):
        index = self._makeOne()
        dummy = self._makeDummy()
        self.assertRaises(ValueError, index.__setitem__, 'nonesuch', dummy)

    def test___setitem___valid_key(self):
        index = self._makeOne()
        dummy = self._makeDummy()
        index['dummy-1.0'] = dummy
        self.assertTrue(index['dummy-1.0'] is dummy)
        self.assertEqual(len(index), 1)
        self.assertEqual(len(index.keys()), 1)
        self.assertEqual(list(index.keys())[0], 'dummy-1.0')
        self.assertEqual(len(index.values()), 1)
        self.assertEqual(list(index.values())[0], dummy)
        self.assertEqual(len(index.items()), 1)
        self.assertEqual(list(index.items())[0], ('dummy-1.0', dummy))

    def test_add_not_dist(self):
        index = self._makeOne()
        class NotDistribution:
            name = 'dummy'
            version = '1.0'
        dummy = NotDistribution()
        self.assertRaises(ValueError, index.add, dummy)

    def test_add_valid_dist(self):
        index = self._makeOne()
        dummy = self._makeDummy()
        index.add(dummy)
        self.assertTrue(index['dummy-1.0'] is dummy)
        self.assertEqual(len(index), 1)
        self.assertEqual(len(index.keys()), 1)
        self.assertEqual(list(index.keys())[0], 'dummy-1.0')
        self.assertEqual(len(index.values()), 1)
        self.assertEqual(list(index.values())[0], dummy)
        self.assertEqual(len(index.items()), 1)
        self.assertEqual(list(index.items())[0], ('dummy-1.0', dummy))
