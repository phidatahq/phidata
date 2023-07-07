import io
import os
import tarfile
import zipfile

from .distribution import Distribution

class SDist(Distribution):

    def __init__(self, filename, metadata_version=None):
        self.filename = filename
        self.metadata_version = metadata_version
        self.extractMetadata()

    @classmethod
    def _get_archive(cls, fqn):
        if not os.path.exists(fqn):
            raise ValueError('No such file: %s' % fqn)

        if zipfile.is_zipfile(fqn):
            archive = zipfile.ZipFile(fqn)
            names = archive.namelist()
            def read_file(name):
                return archive.read(name)
        elif tarfile.is_tarfile(fqn):
            archive = tarfile.TarFile.open(fqn)
            names = archive.getnames()
            def read_file(name):
                return archive.extractfile(name).read()
        else:
            raise ValueError('Not a known archive format: %s' % fqn)

        return archive, names, read_file


    def read(self):
        fqn = os.path.abspath(
                os.path.normpath(self.filename))

        archive, names, read_file = self._get_archive(fqn)

        try:
            tuples = [x.split('/') for x in names if 'PKG-INFO' in x]
            schwarz = sorted([(len(x), x) for x in tuples])
            for path in [x[1] for x in schwarz]:
                candidate = '/'.join(path)
                data = read_file(candidate)
                if b'Metadata-Version' in data:
                    return data
        finally:
            archive.close()

        raise ValueError('No PKG-INFO in archive: %s' % fqn)


class UnpackedSDist(SDist):
    def __init__(self, filename, metadata_version=None):
        if os.path.isdir(filename):
            pass
        elif os.path.isfile(filename):
            filename = os.path.dirname(filename)
        else:
            raise ValueError('No such file: %s' % filename)

        super(UnpackedSDist, self).__init__(
                filename, metadata_version=metadata_version)

    def read(self):
        try:
            pkg_info = os.path.join(self.filename, 'PKG-INFO')
            with io.open(pkg_info, errors='ignore') as f:
                return f.read()
        except Exception as e:
            raise ValueError('Could not load %s as an unpacked sdist: %s'
                                % (self.filename, e))
