import unittest

class WheelTests(unittest.TestCase):

    def _getTargetClass(self):
        from pkginfo.wheel import Wheel
        return Wheel

    def _makeOne(self, filename=None, metadata_version=None):
        if metadata_version is not None:
            return self._getTargetClass()(filename, metadata_version)
        return self._getTargetClass()(filename)

    def _checkSample(self, wheel, filename):
        self.assertEqual(wheel.filename, filename)
        self.assertEqual(wheel.name, 'mypackage')
        self.assertEqual(wheel.version, '0.1')
        self.assertEqual(wheel.keywords, None)

    def _checkClassifiers(self, wheel):
        self.assertEqual(list(wheel.classifiers),
                         ['Development Status :: 4 - Beta',
                          'Environment :: Console (Text Based)',
                         ])
        self.assertEqual(list(wheel.supported_platforms), [])

    def test_ctor_w_bogus_filename(self):
        import os
        d, _ = os.path.split(__file__)
        filename = '%s/../../docs/examples/nonesuch-0.1-any.whl' % d
        self.assertRaises(ValueError, self._makeOne, filename)

    def test_ctor_w_non_wheel(self):
        import os
        d, _ = os.path.split(__file__)
        filename = '%s/../../docs/examples/mypackage-0.1.zip' % d
        self.assertRaises(ValueError, self._makeOne, filename)

    def test_ctor_wo_dist_info(self):
        import os
        d, _ = os.path.split(__file__)
        filename = '%s/../../docs/examples/nodistinfo-0.1-any.whl' % d
        self.assertRaises(ValueError, self._makeOne, filename)

    def test_ctor_w_valid_wheel(self):
        import os
        d, _ = os.path.split(__file__)
        filename = ('%s/../../docs/examples/'
                    'mypackage-0.1-cp26-none-linux_x86_64.whl') % d
        wheel = self._makeOne(filename)
        self.assertEqual(wheel.metadata_version, '2.0')
        self._checkSample(wheel, filename)
        self._checkClassifiers(wheel)

    def test_ctor_w_installed_wheel(self):
        import os
        d, _ = os.path.split(__file__)
        filename = (
            '%s/../../docs/examples/mypackage-0.1.dist-info') % d
        wheel = self._makeOne(filename)
        self.assertEqual(wheel.metadata_version, '2.0')
        self._checkSample(wheel, filename)
        self._checkClassifiers(wheel)

    def test_ctor_w_valid_wheel_and_metadata_version(self):
        import os
        d, _ = os.path.split(__file__)
        filename = ('%s/../../docs/examples/'
                    'mypackage-0.1-cp26-none-linux_x86_64.whl') % d
        wheel = self._makeOne(filename, metadata_version='1.1')
        self.assertEqual(wheel.metadata_version, '1.1')
        self._checkSample(wheel, filename)
        self._checkClassifiers(wheel)

    def test_ctor_w_valid_wheel_w_description_header(self):
        import os
        d, _ = os.path.split(__file__)
        filename = ('%s/../../docs/examples/'
                    'distlib-0.3.1-py2.py3-none-any.whl') % d
        wheel = self._makeOne(filename, metadata_version='1.1')
        self.assertEqual(wheel.metadata_version, '1.1')
        self.assertTrue(wheel.description)

    def test_ctor_w_valid_wheel_w_description_body(self):
        import os
        d, _ = os.path.split(__file__)
        filename = ('%s/../../docs/examples/'
                    'testlp1974172-0.0.0-py3-none-any.whl') % d
        wheel = self._makeOne(filename, metadata_version='2.1')
        self.assertEqual(wheel.metadata_version, '2.1')
        self.assertIn(
            "https://bugs.launchpad.net/pkginfo/+bug/1885458",
            wheel.description
        )

    def test_ctor_w_valid_installed_wheel(self):
        import os
        import shutil
        import tempfile
        import zipfile

        d, _ = os.path.split(__file__)
        filename = ('%s/../../docs/examples/'
                    'mypackage-0.1-cp26-none-linux_x86_64.whl') % d

        try:
            # note: we mock a wheel installation by unzipping
            test_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(filename) as zipf:
                zipf.extractall(test_dir)
            wheel = self._makeOne(filename)
            self.assertEqual(wheel.metadata_version, '2.0')
            self._checkSample(wheel, filename)
            self._checkClassifiers(wheel)
        finally:
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)
