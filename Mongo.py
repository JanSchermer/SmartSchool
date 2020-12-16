from os import getenv
from pymongo import MongoClient

# Default database name to use
DEFAULT_DATABASE = getenv("SMART_SCHOOL_DEFAULT_DB", "SmartSchool")

class DBClient:

    def __init__(self, connection):
        """
        Initializing database with given mongodb connection string.
        """
        self.client = MongoClient(connection)

    def getClient(self):
        """
        :return MongoDB client object
        """
        return self.client

    def getDataBase(self):
        """
        :return MongoDB database of default name
        """
        return self.client[DEFAULT_DATABASE]


