import numpy as np
try: from future_builtins import zip
except ImportError: pass

from .tracesortingformat import TraceSortingFormat as Sorting
from .trace import Sequence
from .utils import castarray

class Depth(Sequence):
    """
    The Depth implements the array interface, where every array element, the
    depth, is a numpy.ndarray of a horizontal cut of the volume. As all arrays
    it can be random accessed, iterated over, and read strided. Please note
    that SEG-Y data is laid out trace-by-trace on disk, so accessing horizontal
    cuts (fixed z-coordinates in a cartesian grid) is *very* inefficient.

    Notes
    -----
    .. versionadded:: 1.1

    .. versionchanged:: 1.6
        common list operations (collections.Sequence)

    .. warning::
        Accessing the file by depth (fixed z-coordinate) is inefficient because
        of poor locality and many reads. If you read more than a handful
        depths, consider using a faster mode.
    """

    def __init__(self, fd):
        super(Depth, self).__init__(len(fd.samples))
        self.filehandle = fd.xfd
        self.dtype = fd.dtype

        if fd.unstructured:
            self.shape = fd.tracecount
        elif fd.sorting == Sorting.CROSSLINE_SORTING:
            self.shape = (len(fd.ilines), len(fd.xlines))
        else:
            self.shape = (len(fd.xlines), len(fd.ilines))

        self.offsets = len(fd.offsets)

    def __getitem__(self, i):
        """depth[i]

        ith depth, a horizontal cross-section of the file, starting at 0.
        depth[i] returns a numpy.ndarray, and changes to this array will *not*
        be reflected on disk.

        When i is a slice, a generator of numpy.ndarray is returned.

        Parameters
        ----------
        i : int or slice

        Returns
        -------
        depth : numpy.ndarray of dtype or generator of numpy.ndarray of dtype

        Notes
        -----
        .. versionadded:: 1.1

        Behaves like [] for lists.

        Examples
        --------
        Read a single cut (one sample per trace):

        >>> x = f.depth_slice[199]

        Copy every depth slice into a list:

        >>> l = [numpy.copy(x) for x in depth[:]

        Every third depth:

        >>> for d in depth[::3]:
        ...     (d * 6).mean()

        Read up to 250:

        >>> for d in depth[:250]:
        ...     d.mean()
        """

        try:
            i = self.wrapindex(i)
            buf = np.empty(self.shape, dtype=self.dtype)
            return self.filehandle.getdepth(i, buf.size, self.offsets, buf)

        except TypeError:
            def gen():
                x = np.empty(self.shape, dtype=self.dtype)
                y = np.copy(x)

                for j in range(*i.indices(len(self))):
                    self.filehandle.getdepth(j, x.size, self.offsets, x)
                    x, y = y, x
                    yield y

            return gen()

    def __setitem__(self, depth, val):
        """depth[i] = val

        Write the ith depth, a horizontal cross-section, of the file, starting
        at 0. It accepts any array_like, but `val` must be at least as big as
        the underlying data slice.

        If `val` is longer than the underlying trace, `val` is essentially truncated.

        Parameters
        ----------
        i   : int or slice
        val : array_like

        Notes
        -----
        .. versionadded:: 1.1

        Behaves like [] for lists.

        Examples
        --------
        Copy a depth:

        >>> depth[4] = other[19]

        Copy consecutive depths, and assign to a sub volume (inject a sub cube
        into the larger volume):

        >>> depth[10:50] = other[:]

        Copy into every other depth from an iterable:

        >>> depth[::2] = other
        """
        if isinstance(depth, slice):
            for i, x in zip(range(*depth.indices(len(self))), val):
                self[i] = x
            return

        val = castarray(val, dtype = self.dtype)
        self.filehandle.putdepth(depth, val.size, self.offsets, val)
