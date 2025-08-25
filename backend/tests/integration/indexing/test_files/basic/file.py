def simple_fn():
    return 1


class SimpleClass:

    def __init__(self):
        pass

    def simple_method(self):
        return 2


def outer_fn():

    def inner_fn():
        return 3

    class InnerClass:
        pass

    return 4


class OuterClass:

    class InnerClass:
        pass
