def simple_fn():
    # file.simple_fn
    return 1


class SimpleClass:
    # file.SimpleClass

    def __init__(self):
        # file.SimpleClass.__init__
        # file.SimpleClass -> file.SimpleClass.__init__
        pass

    def simple_method(self):
        # file.SimpleClass.simple_method
        # file.SimpleClass -> file.SimpleClass.simple_method
        return 2


def parent_fn(y) -> int:
    # file.parent_fn

    def child_fn(x: int) -> int:
        # file.parent_fn.child_fn
        # file.parent_fn -> file.parent_fn.child_fn
        return x * x

    # file.parent_fn -> file.parent_fn.child_fn
    return y + child_fn(y)


def recursive_fn(x: int) -> int:
    # file.recursive_fn

    # file.recursive_fn -> file.recursive_fn
    return 1 if x <= 1 else x * recursive_fn(x - 1)


class ParentClass:
    # file.ParentClass

    class ChildClass:
        # file.ParentClass.ChildClass
        # file.ParentClass -> file.ParentClass.ChildClass
        pass
