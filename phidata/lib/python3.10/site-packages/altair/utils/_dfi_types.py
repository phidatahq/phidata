# DataFrame Interchange Protocol Types
# Copied from https://data-apis.org/dataframe-protocol/latest/API.html,
# changed ABCs to Protocols, and subset the type hints to only those that are
# relevant for Altair.
#
# These classes are only for use in type signatures
import enum
from typing import Any, Iterable, Optional, Tuple, Protocol


class DtypeKind(enum.IntEnum):
    """
    Integer enum for data types.

    Attributes
    ----------
    INT : int
        Matches to signed integer data type.
    UINT : int
        Matches to unsigned integer data type.
    FLOAT : int
        Matches to floating point data type.
    BOOL : int
        Matches to boolean data type.
    STRING : int
        Matches to string data type (UTF-8 encoded).
    DATETIME : int
        Matches to datetime data type.
    CATEGORICAL : int
        Matches to categorical data type.
    """

    INT = 0
    UINT = 1
    FLOAT = 2
    BOOL = 20
    STRING = 21  # UTF-8
    DATETIME = 22
    CATEGORICAL = 23


# Type hint of first element would actually be DtypeKind but can't use that
# as other libraries won't use an instance of our own Enum in this module but have
# their own. Type checkers will raise an error on that even though the enums
# are identical.
Dtype = Tuple[Any, int, str, str]  # see Column.dtype


class Column(Protocol):
    @property
    def dtype(self) -> Dtype:
        """
        Dtype description as a tuple ``(kind, bit-width, format string, endianness)``.

        Bit-width : the number of bits as an integer
        Format string : data type description format string in Apache Arrow C
                        Data Interface format.
        Endianness : current only native endianness (``=``) is supported

        Notes:
            - Kind specifiers are aligned with DLPack where possible (hence the
              jump to 20, leave enough room for future extension)
            - Masks must be specified as boolean with either bit width 1 (for bit
              masks) or 8 (for byte masks).
            - Dtype width in bits was preferred over bytes
            - Endianness isn't too useful, but included now in case in the future
              we need to support non-native endianness
            - Went with Apache Arrow format strings over NumPy format strings
              because they're more complete from a dataframe perspective
            - Format strings are mostly useful for datetime specification, and
              for categoricals.
            - For categoricals, the format string describes the type of the
              categorical in the data buffer. In case of a separate encoding of
              the categorical (e.g. an integer to string mapping), this can
              be derived from ``self.describe_categorical``.
            - Data types not included: complex, Arrow-style null, binary, decimal,
              and nested (list, struct, map, union) dtypes.
        """
        pass

    # Have to use a generic Any return type as not all libraries who implement
    # the dataframe interchange protocol implement the TypedDict that is usually
    # returned here in the same way. As TypedDicts are invariant, even a slight change
    # will lead to an error by a type checker. See PR in which this code was added
    # for details.
    @property
    def describe_categorical(self) -> Any:
        """
        If the dtype is categorical, there are two options:
        - There are only values in the data buffer.
        - There is a separate non-categorical Column encoding categorical values.

        Raises TypeError if the dtype is not categorical

        Returns the dictionary with description on how to interpret the data buffer:
            - "is_ordered" : bool, whether the ordering of dictionary indices is
                             semantically meaningful.
            - "is_dictionary" : bool, whether a mapping of
                                categorical values to other objects exists
            - "categories" : Column representing the (implicit) mapping of indices to
                             category values (e.g. an array of cat1, cat2, ...).
                             None if not a dictionary-style categorical.

        TBD: are there any other in-memory representations that are needed?
        """
        pass


class DataFrame(Protocol):
    """
    A data frame class, with only the methods required by the interchange
    protocol defined.

    A "data frame" represents an ordered collection of named columns.
    A column's "name" must be a unique string.
    Columns may be accessed by name or by position.

    This could be a public data frame class, or an object with the methods and
    attributes defined on this DataFrame class could be returned from the
    ``__dataframe__`` method of a public data frame class in a library adhering
    to the dataframe interchange protocol specification.
    """

    def __dataframe__(
        self, nan_as_null: bool = False, allow_copy: bool = True
    ) -> "DataFrame":
        """
        Construct a new exchange object, potentially changing the parameters.

        ``nan_as_null`` is a keyword intended for the consumer to tell the
        producer to overwrite null values in the data with ``NaN``.
        It is intended for cases where the consumer does not support the bit
        mask or byte mask that is the producer's native representation.
        ``allow_copy`` is a keyword that defines whether or not the library is
        allowed to make a copy of the data. For example, copying data would be
        necessary if a library supports strided buffers, given that this protocol
        specifies contiguous buffers.
        """
        pass

    def column_names(self) -> Iterable[str]:
        """
        Return an iterator yielding the column names.
        """
        pass

    def get_column_by_name(self, name: str) -> Column:
        """
        Return the column whose name is the indicated name.
        """
        pass

    def get_chunks(self, n_chunks: Optional[int] = None) -> Iterable["DataFrame"]:
        """
        Return an iterator yielding the chunks.

        By default (None), yields the chunks that the data is stored as by the
        producer. If given, ``n_chunks`` must be a multiple of
        ``self.num_chunks()``, meaning the producer must subdivide each chunk
        before yielding it.

        Note that the producer must ensure that all columns are chunked the
        same way.
        """
        pass
