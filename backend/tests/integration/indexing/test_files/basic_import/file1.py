import file2
from module.file3 import Class3a, func3a, func3b

a = func3a()


def func1a():
    return file2.func2a()


class Class1a(Class3a):
    def method_a(cls: file2.Class2a):
        a = cls()
        return func3b() + super().method_a()
