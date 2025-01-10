from dataclasses import dataclass, asdict
from typing import Type

# Define a custom dataclass decorator
def AgnoDataClass(cls: Type) -> Type:
    # Apply the dataclass transformation
    # Define the custom method
    def to_dict_exclude_none(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}

    # Attach the method to the class
    setattr(cls, "to_dict_exclude_none", to_dict_exclude_none)

    return cls



class my_decorator():
    def __init__(self, arg):
        pass

    def __call__(self, func):
        @dataclass  # <--- Just include the lib's decorator here
        def do_athing(*args, **kwargs):
            func(*args, **kwargs)

        return do_athing

# Usage of the custom decorator
@AgnoDataClass
@dataclass
class User():
    id: int
    name: str
    email: str = None

# Example usage
user = User(id=1, name="Alice")
print(user.)  # {'id': 1, 'name': 'Alice'}
