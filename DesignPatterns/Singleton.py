import sqlite3
import threading


class Singleton(object):
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(Singleton, cls).__new__(cls)
        return cls.instance


s1 = Singleton()
s2 = Singleton()

print(s1 is s2)


class DatabaseSingleton:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DatabaseSingleton, cls).__new__(cls)
                    cls._instance.conn = sqlite3.connect("database.db")
        return cls._instance

# https://softwarepatterns.com/python/singleton-software-pattern-python-example


class ThreadsafeSingleton:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance


import threading
import psycopg2
from psycopg2 import pool

class DatabaseConnectionPool:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, minconn=1, maxconn=5, **db_params):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:  # Double-checked locking
                    cls._instance = super().__new__(cls)
                    cls._instance._pool = pool.SimpleConnectionPool(
                        minconn, maxconn, **db_params
                    )
        return cls._instance

    def get_connection(self):
        return self._pool.getconn()

    def release_connection(self, conn):
        self._pool.putconn(conn)

    def close_all(self):
        self._pool.closeall()

# Usage
db_params = {
    "user": "postgres",
    "password": "secret",
    "host": "localhost",
    "port": "5432",
    "database": "mydb"
}

pool_instance = DatabaseConnectionPool(minconn=1, maxconn=10, **db_params)
conn = pool_instance.get_connection()

# Do work
cursor = conn.cursor()
cursor.execute("SELECT NOW();")
print(cursor.fetchone())

pool_instance.release_connection(conn)
