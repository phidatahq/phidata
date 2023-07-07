import unittest

class BDistTests(unittest.TestCase):

    def _getTargetClass(self):
        from pkginfo.bdist import BDist
        return BDist

    def _makeOne(self, filename=None, metadata_version=None):
        if metadata_version is not None:
            return self._getTargetClass()(filename, metadata_version)
        return self._getTargetClass()(filename)

    def _checkSample(self, bdist, filename):
        self.assertEqual(bdist.filename, filename)
        self.assertEqual(bdist.name, 'mypackage')
        self.assertEqual(bdist.version, '0.1')
        self.assertEqual(bdist.keywords, None)

    def _checkClassifiers(self, bdist):
        self.assertEqual(list(bdist.classifiers),
                         ['Development Status :: 4 - Beta',
                          'Environment :: Console (Text Based)',
                         ])
        self.assertEqual(list(bdist.supported_platforms), [])

    def test_ctor_w_bogus_filename(self):
        import os
        d, _ = os.path.split(__file__)
        filename = '%s/../../docs/examples/nonesuch-0.1-py2.6.egg' % d
        self.assertRaises(ValueError, self._makeOne, filename)

    def test_ctor_w_non_egg(self):
        import os
        d, _ = os.path.split(__file__)
        filename = '%s/../../docs/examples/mypackage-0.1.zip' % d
        self.assertRaises(ValueError, self._makeOne, filename)

    def test_ctor_wo_PKG_INFO(self):
        import os
        d, _ = os.path.split(__file__)
        filename = '%s/../../docs/examples/nopkginfo-0.1.egg' % d
        self.assertRaises(ValueError, self._makeOne, filename)

    def test_ctor_w_egg(self):
        import os
        d, _ = os.path.split(__file__)
        filename = '%s/../../docs/examples/mypackage-0.1-py2.6.egg' % d
        bdist = self._makeOne(filename)
        self.assertEqual(bdist.metadata_version, '1.0')
        self._checkSample(bdist, filename)

    def test_ctor_w_egg_and_metadata_version(self):
        import os
        d, _ = os.path.split(__file__)
        filename = '%s/../../docs/examples/mypackage-0.1-py2.6.egg' % d
        bdist = self._makeOne(filename, metadata_version='1.1')
        self.assertEqual(bdist.metadata_version, '1.1')
        self._checkSample(bdist, filename)
        self._checkClassifiers(bdist)
