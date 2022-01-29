class Singleton(object):
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(Singleton, cls).__new__(cls)
        return cls.instance


s = Singleton()
print("Object created", s)
s1 = Singleton()
print("Object created", s1)


class Singleton:
    __instance = None

    def __init__(self):
        if not Singleton.__instance:
            print(" __init__ method called..")
        else:
            print("Instance already created:", self.get_instance())

    @classmethod
    def get_instance(cls):
        if not cls.__instance:
            cls.__instance = Singleton()
        return cls.__instance


s = Singleton()  ## class initialized, but object not created
print("Object created", Singleton.get_instance())  # Object gets created here
s1 = Singleton()  ## instance already created
