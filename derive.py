def derive(*callbacks: [callable]) -> "Derive":
    class Derive(type):
        def __new__(cls, name, bases, env, *args, **kwargs):
            for cb in callbacks:
                cls, name, bases, env = cb(cls, name, bases, env, *args, **kwargs)
            return type.__new__(cls, name, bases, env)
    return Derive

def call_without_args(x):
    return x()

def is_value(val):
    """
    val is instance of type instance,
    type instance is class,
    so, val is class instance.
    """
    return isinstance(val, object) and not isinstance(val, type)

"""
# NOTE use type or object or class must be careful
# NOTE don't use subclass
# because of
# >> isinstance(type, object) is isinstance(object, type)
# => True
# >> isinstance(int, type) is True
# => True
# <class 'int'> is type instance
# >> isinstance(1, type) is True
# => False
# 1 is int instance, so 1 is instance of type instance
# >> isinstance(int, object)
# => True
# ... evil, 'anything is object' is evil

# type construct is class
# value is class instance

Inductive list (A: Type) : Type  :=
 | nil : list A
 | cons : A -> list A -> list A.
# instance 'a List Show ...
"""

__all__ = ["derive", "is_value", "call_without_args"]

def __dir__():
    return __all__
