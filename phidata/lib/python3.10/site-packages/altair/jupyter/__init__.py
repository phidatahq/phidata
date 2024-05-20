try:
    import anywidget  # noqa: F401
except ImportError:
    # When anywidget isn't available, create stand-in JupyterChart class
    # that raises an informative import error on construction. This
    # way we can make JupyterChart available in the altair namespace
    # when anywidget is not installed
    class JupyterChart:
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "The Altair JupyterChart requires the anywidget \n"
                "Python package which may be installed using pip with\n"
                "    pip install anywidget\n"
                "or using conda with\n"
                "    conda install -c conda-forge anywidget\n"
                "Afterwards, you will need to restart your Python kernel."
            )

else:
    from .jupyter_chart import JupyterChart  # noqa: F401
