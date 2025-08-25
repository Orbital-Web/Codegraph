import file2
import module2.file4 as f4

from module1 import func3a as f3a
from module1.file3 import Class3a, func4a

a = file2.func2a()  # file1.file2.func2a -> file2.func2a

b = f4.func4b()  # file1.f4.func4b -> module2.file4.func4b

c = f3a()  # file1.f3a -> module1.func3a

d = Class3a()  # file1.Class3a -> module1.file3.Class3a
e = func4a()  # file1.func4a -> module1.file3.func4a -> module2.file4.func4a


def func1a():
    from file2 import func2b

    f = func2b()  # file.func2b -> file2.func2b
