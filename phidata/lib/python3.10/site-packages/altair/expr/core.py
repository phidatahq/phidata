from ..utils import SchemaBase


class DatumType:
    """An object to assist in building Vega-Lite Expressions"""

    def __repr__(self):
        return "datum"

    def __getattr__(self, attr):
        if attr.startswith("__") and attr.endswith("__"):
            raise AttributeError(attr)
        return GetAttrExpression("datum", attr)

    def __getitem__(self, attr):
        return GetItemExpression("datum", attr)

    def __call__(self, datum, **kwargs):
        """Specify a datum for use in an encoding"""
        return dict(datum=datum, **kwargs)


datum = DatumType()


def _js_repr(val):
    """Return a javascript-safe string representation of val"""
    if val is True:
        return "true"
    elif val is False:
        return "false"
    elif val is None:
        return "null"
    elif isinstance(val, OperatorMixin):
        return val._to_expr()
    else:
        return repr(val)


# Designed to work with Expression and VariableParameter
class OperatorMixin:
    def _to_expr(self):
        return repr(self)

    def _from_expr(self, expr):
        return expr

    def __add__(self, other):
        comp_value = BinaryExpression("+", self, other)
        return self._from_expr(comp_value)

    def __radd__(self, other):
        comp_value = BinaryExpression("+", other, self)
        return self._from_expr(comp_value)

    def __sub__(self, other):
        comp_value = BinaryExpression("-", self, other)
        return self._from_expr(comp_value)

    def __rsub__(self, other):
        comp_value = BinaryExpression("-", other, self)
        return self._from_expr(comp_value)

    def __mul__(self, other):
        comp_value = BinaryExpression("*", self, other)
        return self._from_expr(comp_value)

    def __rmul__(self, other):
        comp_value = BinaryExpression("*", other, self)
        return self._from_expr(comp_value)

    def __truediv__(self, other):
        comp_value = BinaryExpression("/", self, other)
        return self._from_expr(comp_value)

    def __rtruediv__(self, other):
        comp_value = BinaryExpression("/", other, self)
        return self._from_expr(comp_value)

    __div__ = __truediv__

    __rdiv__ = __rtruediv__

    def __mod__(self, other):
        comp_value = BinaryExpression("%", self, other)
        return self._from_expr(comp_value)

    def __rmod__(self, other):
        comp_value = BinaryExpression("%", other, self)
        return self._from_expr(comp_value)

    def __pow__(self, other):
        # "**" Javascript operator is not supported in all browsers
        comp_value = FunctionExpression("pow", (self, other))
        return self._from_expr(comp_value)

    def __rpow__(self, other):
        # "**" Javascript operator is not supported in all browsers
        comp_value = FunctionExpression("pow", (other, self))
        return self._from_expr(comp_value)

    def __neg__(self):
        comp_value = UnaryExpression("-", self)
        return self._from_expr(comp_value)

    def __pos__(self):
        comp_value = UnaryExpression("+", self)
        return self._from_expr(comp_value)

    # comparison operators

    def __eq__(self, other):
        comp_value = BinaryExpression("===", self, other)
        return self._from_expr(comp_value)

    def __ne__(self, other):
        comp_value = BinaryExpression("!==", self, other)
        return self._from_expr(comp_value)

    def __gt__(self, other):
        comp_value = BinaryExpression(">", self, other)
        return self._from_expr(comp_value)

    def __lt__(self, other):
        comp_value = BinaryExpression("<", self, other)
        return self._from_expr(comp_value)

    def __ge__(self, other):
        comp_value = BinaryExpression(">=", self, other)
        return self._from_expr(comp_value)

    def __le__(self, other):
        comp_value = BinaryExpression("<=", self, other)
        return self._from_expr(comp_value)

    def __abs__(self):
        comp_value = FunctionExpression("abs", (self,))
        return self._from_expr(comp_value)

    # logical operators

    def __and__(self, other):
        comp_value = BinaryExpression("&&", self, other)
        return self._from_expr(comp_value)

    def __rand__(self, other):
        comp_value = BinaryExpression("&&", other, self)
        return self._from_expr(comp_value)

    def __or__(self, other):
        comp_value = BinaryExpression("||", self, other)
        return self._from_expr(comp_value)

    def __ror__(self, other):
        comp_value = BinaryExpression("||", other, self)
        return self._from_expr(comp_value)

    def __invert__(self):
        comp_value = UnaryExpression("!", self)
        return self._from_expr(comp_value)


class Expression(OperatorMixin, SchemaBase):
    """Expression

    Base object for enabling build-up of Javascript expressions using
    a Python syntax. Calling ``repr(obj)`` will return a Javascript
    representation of the object and the operations it encodes.
    """

    _schema = {"type": "string"}

    def to_dict(self, *args, **kwargs):
        return repr(self)

    def __setattr__(self, attr, val):
        # We don't need the setattr magic defined in SchemaBase
        return object.__setattr__(self, attr, val)

    # item access
    def __getitem__(self, val):
        return GetItemExpression(self, val)


class UnaryExpression(Expression):
    def __init__(self, op, val):
        super(UnaryExpression, self).__init__(op=op, val=val)

    def __repr__(self):
        return "({op}{val})".format(op=self.op, val=_js_repr(self.val))


class BinaryExpression(Expression):
    def __init__(self, op, lhs, rhs):
        super(BinaryExpression, self).__init__(op=op, lhs=lhs, rhs=rhs)

    def __repr__(self):
        return "({lhs} {op} {rhs})".format(
            op=self.op, lhs=_js_repr(self.lhs), rhs=_js_repr(self.rhs)
        )


class FunctionExpression(Expression):
    def __init__(self, name, args):
        super(FunctionExpression, self).__init__(name=name, args=args)

    def __repr__(self):
        args = ",".join(_js_repr(arg) for arg in self.args)
        return "{name}({args})".format(name=self.name, args=args)


class ConstExpression(Expression):
    def __init__(self, name, doc):
        self.__doc__ = """{}: {}""".format(name, doc)
        super(ConstExpression, self).__init__(name=name, doc=doc)

    def __repr__(self):
        return str(self.name)


class GetAttrExpression(Expression):
    def __init__(self, group, name):
        super(GetAttrExpression, self).__init__(group=group, name=name)

    def __repr__(self):
        return "{}.{}".format(self.group, self.name)


class GetItemExpression(Expression):
    def __init__(self, group, name):
        super(GetItemExpression, self).__init__(group=group, name=name)

    def __repr__(self):
        return "{}[{!r}]".format(self.group, self.name)
