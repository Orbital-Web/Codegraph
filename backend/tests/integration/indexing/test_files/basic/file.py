# file


def simple_fn():
    # file.simple_fn
    return 1


class SimpleClass:
    # file.SimpleClass

    def __init__(self):
        # file.SimpleClass.__init__
        # file.SimpleClass -> file.SimpleClass.__init__ (cls, fn)
        pass

    def simple_method(self):
        # file.SimpleClass.simple_method
        # file.SimpleClass -> file.SimpleClass.simple_method (cls, fn)
        return 2


def parent_fn(y) -> int:
    # file.parent_fn

    class ChildClass(SimpleClass):
        # file.parent_fn.ChildClass
        # file.parent_fn -> file.parent_fn.ChildClass (fn, cls)
        # file.parent_fn.ChildClass -> file.SimpleClass (cls, cls)
        pass

    def child_fn(x: int, z: SimpleClass) -> int:
        # file.parent_fn.child_fn
        # file.parent_fn -> file.parent_fn.child_fn (fn, fn)
        # file.parent_fn -> file.SimpleClass (fn, cls)

        # file.parent_fn -> file.SimpleClass.simple_method (fn, fn)
        return x * x + z.simple_method()

    # file.parent_fn -> file.parent_fn.child_fn (fn, fn)
    return y + child_fn(y)


def recursive_fn(x: int) -> int:
    # file.recursive_fn

    # file.recursive_fn -> file.recursive_fn (fn, fn (self))
    return 1 if x <= 1 else x * recursive_fn(x - 1)


class ParentClass:
    # file.ParentClass

    class ChildClass:
        # file.ParentClass.ChildClass
        # file.ParentClass -> file.ParentClass.ChildClass (cls, cls)
        pass
