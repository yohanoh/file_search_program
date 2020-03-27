import os


def fun():
    pwd = "Data/"
    try:
        for i in range(10000000):
            print(i)
            temp = "test" + str(i)
            os.makedirs(os.path.join(pwd, temp))
            pwd = pwd + "\\" + temp
    except FileNotFoundError:
        return

fun()