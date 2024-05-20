from django import forms
import numpy as np


class VectorWidget(forms.TextInput):
    def format_value(self, value):
        if isinstance(value, np.ndarray):
            value = value.tolist()
        return super().format_value(value)
