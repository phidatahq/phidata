import ast
import sys


class _CatchDisplay:
    """Class to temporarily catch sys.displayhook"""

    def __init__(self):
        self.output = None

    def __enter__(self):
        self.old_hook = sys.displayhook
        sys.displayhook = self
        return self

    def __exit__(self, type, value, traceback):
        sys.displayhook = self.old_hook
        # Returning False will cause exceptions to propagate
        return False

    def __call__(self, output):
        self.output = output


def eval_block(code, namespace=None, filename="<string>"):
    """
    Execute a multi-line block of code in the given namespace

    If the final statement in the code is an expression, return
    the result of the expression.
    """
    tree = ast.parse(code, filename="<ast>", mode="exec")
    if namespace is None:
        namespace = {}
    catch_display = _CatchDisplay()

    if isinstance(tree.body[-1], ast.Expr):
        to_exec, to_eval = tree.body[:-1], tree.body[-1:]
    else:
        to_exec, to_eval = tree.body, []

    for node in to_exec:
        compiled = compile(ast.Module([node], []), filename=filename, mode="exec")
        exec(compiled, namespace)

    with catch_display:
        for node in to_eval:
            compiled = compile(
                ast.Interactive([node]), filename=filename, mode="single"
            )
            exec(compiled, namespace)

    return catch_display.output
