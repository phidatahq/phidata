import shutil
import tempfile
import unittest

class SDistTests(unittest.TestCase):

    def _getTargetClass(self):
        from pkginfo.sdist import SDist
        return SDist

    def _makeOne(self, filename=None, metadata_version=None):
        if metadata_version is not None:
            return self._getTargetClass()(filename, metadata_version)
        return self._getTargetClass()(filename)

    def _checkSample(self, sdist, filename):
        self.assertEqual(sdist.filename, filename)
        self.assertEqual(sdist.name, 'mypackage')
        self.assertEqual(sdist.version, '0.1')
        self.assertEqual(sdist.keywords, None)
        self.assertEqual(list(sdist.supported_platforms), [])

    def _checkClassifiers(self, sdist):
        self.assertEqual(list(sdist.classifiers),
                         ['Development Status :: 4 - Beta',
                          'Environment :: Console (Text Based)',
                         ])

    def test_ctor_w_invalid_filename(self):
        import os
        d, _ = os.path.split(__file__)
        filename = '%s/../../docs/examples/nonesuch-0.1.tar.gz' % d
        self.assertRaises(ValueError, self._makeOne, filename)

    def test_ctor_wo_PKG_INFO(self):
        import os
        d, _ = os.path.split(__file__)
        filename = '%s/../../docs/examples/nopkginfo-0.1.zip' % d
        self.assertRaises(ValueError, self._makeOne, filename)

    def test_ctor_w_tar(self):
        import os
        d, _ = os.path.split(__file__)
        filename = '%s/../../docs/examples/mypackage-0.1.tar' % d
        sdist = self._makeOne(filename)
        self.assertEqual(sdist.metadata_version, '1.0')
        self._checkSample(sdist, filename)

    def test_ctor_w_gztar(self):
        import os
        d, _ = os.path.split(__file__)
        filename = '%s/../../docs/examples/mypackage-0.1.tar.gz' % d
        sdist = self._makeOne(filename)
        self.assertEqual(sdist.metadata_version, '1.0')
        self._checkSample(sdist, filename)

    def test_ctor_w_gztar_and_metadata_version(self):
        import os
        d, _ = os.path.split(__file__)
        filename = '%s/../../docs/examples/mypackage-0.1.tar.gz' % d
        sdist = self._makeOne(filename, metadata_version='1.1')
        self._checkSample(sdist, filename)
        self.assertEqual(sdist.metadata_version, '1.1')
        self._checkClassifiers(sdist)

    def test_ctor_w_bztar(self):
        import os
        d, _ = os.path.split(__file__)
        filename = '%s/../../docs/examples/mypackage-0.1.tar.bz2' % d
        sdist = self._makeOne(filename)
        self.assertEqual(sdist.metadata_version, '1.0')
        self._checkSample(sdist, filename)

    def test_ctor_w_bztar_and_metadata_version(self):
        import os
        d, _ = os.path.split(__file__)
        filename = '%s/../../docs/examples/mypackage-0.1.tar.bz2' % d
        sdist = self._makeOne(filename, metadata_version='1.1')
        self.assertEqual(sdist.metadata_version, '1.1')
        self._checkSample(sdist, filename)
        self._checkClassifiers(sdist)

    def test_ctor_w_zip(self):
        import os
        d, _ = os.path.split(__file__)
        filename = '%s/../../docs/examples/mypackage-0.1.zip' % d
        sdist = self._makeOne(filename)
        self.assertEqual(sdist.metadata_version, '1.0')
        self._checkSample(sdist, filename)

    def test_ctor_w_zip_and_metadata_version(self):
        import os
        d, _ = os.path.split(__file__)
        filename = '%s/../../docs/examples/mypackage-0.1.zip' % d
        sdist = self._makeOne(filename, metadata_version='1.1')
        self.assertEqual(sdist.metadata_version, '1.1')
        self._checkSample(sdist, filename)
        self._checkClassifiers(sdist)

    def test_ctor_w_bogus(self):
        import os
        d, _ = os.path.split(__file__)
        filename = '%s/../../docs/examples/mypackage-0.1.bogus' % d

        with self.assertRaises(ValueError):
            self._makeOne(filename, metadata_version='1.1')


class UnpackedMixin(object):
    def setUp(self):
        super(UnpackedMixin, self).setUp()
        self.__tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.__tmpdir)
        super(UnpackedMixin, self).tearDown()

    def _getTargetClass(self):
        from pkginfo.sdist import UnpackedSDist
        return UnpackedSDist

    def _getTopDirectory(self):
        import os
        topnames = os.listdir(self.__tmpdir)
        assert len(topnames) == 1
        return os.path.join(self.__tmpdir, topnames[0])

    def _getLoadFilename(self):
        return self._getTopDirectory()

    def _makeOne(self, filename=None, metadata_version=None):

        archive, _, _ = self._getTargetClass()._get_archive(filename)
        try:
            archive.extractall(self.__tmpdir)
        finally:
            archive.close()

        load_filename = self._getLoadFilename()

        if metadata_version is not None:
            return self._getTargetClass()(load_filename, metadata_version)
        return self._getTargetClass()(load_filename)

    def _checkSample(self, sdist, filename):
        filename = self._getTopDirectory()
        super(UnpackedMixin, self)._checkSample(sdist, filename)


class UnpackedSDistGivenDirectoryTests(UnpackedMixin, SDistTests):
    pass

class UnpackedSDistGivenFileSDistTests(UnpackedMixin, SDistTests):
    def _getLoadFilename(self):
        import os
        return os.path.join(self._getTopDirectory(), 'setup.py')
