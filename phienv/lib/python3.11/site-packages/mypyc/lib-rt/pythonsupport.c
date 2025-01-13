// Collects code that was copied in from cpython, for a couple of different reasons:
//  * We wanted to modify it to produce a more efficient version for our uses
//  * We needed to call it and it was static :(
//  * We wanted to call it and needed to backport it

#include "pythonsupport.h"

#if CPY_3_12_FEATURES

// Slow path of CPyLong_AsSsize_tAndOverflow (non-inlined)
Py_ssize_t
CPyLong_AsSsize_tAndOverflow_(PyObject *vv, int *overflow)
{
    PyLongObject *v = (PyLongObject *)vv;
    size_t x, prev;
    Py_ssize_t res;
    Py_ssize_t i;
    int sign;

    *overflow = 0;

    res = -1;
    i = CPY_LONG_TAG(v);

    sign = 1;
    x = 0;
    if (i & CPY_SIGN_NEGATIVE) {
        sign = -1;
    }
    i >>= CPY_NON_SIZE_BITS;
    while (--i >= 0) {
        prev = x;
        x = (x << PyLong_SHIFT) + CPY_LONG_DIGIT(v, i);
        if ((x >> PyLong_SHIFT) != prev) {
            *overflow = sign;
            goto exit;
        }
    }
    /* Haven't lost any bits, but casting to long requires extra
     * care.
     */
    if (x <= (size_t)CPY_TAGGED_MAX) {
        res = (Py_ssize_t)x * sign;
    }
    else if (sign < 0 && x == CPY_TAGGED_ABS_MIN) {
        res = CPY_TAGGED_MIN;
    }
    else {
        *overflow = sign;
        /* res is already set to -1 */
    }
  exit:
    return res;
}

#else

// Slow path of CPyLong_AsSsize_tAndOverflow (non-inlined, Python 3.11 and earlier)
Py_ssize_t
CPyLong_AsSsize_tAndOverflow_(PyObject *vv, int *overflow)
{
    /* This version by Tim Peters */
    PyLongObject *v = (PyLongObject *)vv;
    size_t x, prev;
    Py_ssize_t res;
    Py_ssize_t i;
    int sign;

    *overflow = 0;

    res = -1;
    i = Py_SIZE(v);

    sign = 1;
    x = 0;
    if (i < 0) {
        sign = -1;
        i = -(i);
    }
    while (--i >= 0) {
        prev = x;
        x = (x << PyLong_SHIFT) + CPY_LONG_DIGIT(v, i);
        if ((x >> PyLong_SHIFT) != prev) {
            *overflow = sign;
            goto exit;
        }
    }
    /* Haven't lost any bits, but casting to long requires extra
     * care.
     */
    if (x <= (size_t)CPY_TAGGED_MAX) {
        res = (Py_ssize_t)x * sign;
    }
    else if (sign < 0 && x == CPY_TAGGED_ABS_MIN) {
        res = CPY_TAGGED_MIN;
    }
    else {
        *overflow = sign;
        /* res is already set to -1 */
    }
  exit:
    return res;
}


#endif
