import unittest

class DevelopTests(unittest.TestCase):

    def _getTargetClass(self):
        from pkginfo.develop import Develop
        return Develop

    def _makeOne(self, dirname=None):
        return self._getTargetClass()(dirname)

    def test_ctor_w_path(self):
        from pkginfo.tests import _checkSample
        develop = self._makeOne('.')
        _checkSample(self, develop)

    def test_ctor_w_invalid_path(self):
        import warnings 
        old_filters = warnings.filters[:]
        warnings.filterwarnings('ignore')
        try:
            develop = self._makeOne('/nonesuch')
            self.assertEqual(develop.metadata_version, None)
            self.assertEqual(develop.name, None)
            self.assertEqual(develop.version, None)
        finally:
            warnings.filters[:] = old_filters
