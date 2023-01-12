from phidata.utils.enums import ExtendedEnum


class PVAccessMode(ExtendedEnum):
    # the volume can be mounted as read-write by a single node.
    # ReadWriteOnce access mode still can allow multiple pods to access the volume
    # when the pods are running on the same node.
    READ_WRITE_ONCE = "ReadWriteOnce"
    # the volume can be mounted as read-only by many nodes.
    READ_ONLY_MANY = "ReadOnlyMany"
    # the volume can be mounted as read-write by many nodes.
    READ_WRITE_MANY = "ReadWriteMany"
    # the volume can be mounted as read-write by a single Pod. Use ReadWriteOncePod access mode if
    # you want to ensure that only one pod across whole cluster can read that PVC or write to it.
    READ_WRITE_ONCE_POD = "ReadWriteOncePod"
