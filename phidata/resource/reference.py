class Reference:
    def __init__(self, reference):
        self.reference = reference

    def __call__(self, *args, **kwargs):
        return self.reference(*args, **kwargs)
