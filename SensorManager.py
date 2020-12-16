import random
import string
from os import getenv

from Mongo import DBClient

# Length of generated api keys and ids
KEY_LENGTH = 30
ID_LENGTH = 5

# Database collection names
MASTERS_COLLECTION = getenv("SMART_SCHOOL_MASTERS_COLL", "Masters")
CLIENTS_COLLECTION = getenv("SMART_SCHOOL_CLIENTS_COLL", "Clients")
PERSON_COUNTER_COLLECTION = getenv("SMART_SCHOOL_PERSON_COLL", "PersonCounters")
CO2_SENSOR_COLLECTION = getenv("SMART_SCHOOL_CO2_COLL", "CO2Sensors")


class SensorManager:
    

    def __init__(self, db_client:DBClient, master_key=None):

        # Getting database object from db client
        self.database = db_client.getDataBase()

        # Checking master key, if provided
        if master_key is not None:
            self.check_master(master_key)

        # Refuse master privileges, if master key is not provided
        else:
            self.master = False


    def check_master(self, key):
        """
        Checks master key and grands master privileges, if it's valid
        """

        # Getting masters collection from database
        master_coll = self.database[MASTERS_COLLECTION]

        # Creating query for crawling collection
        query = {"key": key}

        # Granting master privileges, if key was found
        if master_coll.count_documents(query) > 0:
            self.master = True

        # Refusing master privileges, if key is invalid
        else:
            self.master = False


    def create(self, type:str):
        """
        Creates new sensor of given type and returns it's id and api key in
        the fields "id" and "api".
        Requires master privileges to have ben granted.
        """

        # Denying access, if master privileges haven't ben granted
        if not self.master:
            return {"status": "access denied", "hint": "Master key is required!"}

        # Getting clients collection from database
        clients_coll = self.database[CLIENTS_COLLECTION]

        # Getting chars for generation of api key and id
        key_chars = string.ascii_letters + string.digits
        id_chars = string.ascii_uppercase

        # Converting strings into char arrays
        key_chars = list(key_chars)
        id_chars = list(id_chars)

        # Generating random api key and id
        api_key = random.choices(key_chars, k=KEY_LENGTH)
        id = random.choices(id_chars, k=ID_LENGTH)

        # Converting char arrays into strings
        api_key = "".join(api_key)
        id = "".join(id)

        # Creating document for sensor and inserting it into the database
        sensor_doc = {"id": id, "key": api_key, "type": type}
        clients_coll.insert(sensor_doc)

        return {"status": "ok", "id": id, "api": api_key}


    def destroy(self, id):
        """
        Deletes sensor with given id.
        Requires master privileges to have ben granted.
        """

        # Denying access, if master privileges haven't ben granted
        if not self.master:
            return {"status": "access denied", "hint": "Master key is required!"}

        # Getting clients collection from database
        clients_coll = self.database[CLIENTS_COLLECTION]

        query = {"id": id}

        # Checking if id exists in database. If it dose deleting entry, else sending "not found" status.
        if clients_coll.count_documents(query) > 0:
            clients_coll.delete_one(query)

            return {"status": "ok"}

        else:
            return {"status": "not found"}


    def reset(self, id, api=None):
        """
        Resets sensor with given id, if api key is not privileged and master privileges have ben granted.
        If API key is provided, resetting corresponding sensor instead.
        """

        # Initializing "sensor_doc" variable as none
        sensor_doc = None

        # Getting clients collection from database
        clients_coll = self.database[CLIENTS_COLLECTION]

        if api is not None:

            # Creating database for api key
            query = {"key": api}
            sensor_doc = clients_coll.find_one(query)

            # If api key is invalid returning "access denied" status
            if sensor_doc is None:
                return {"status": "access denied", "hint": "API Key is invalid!"}

        # Denying access, if master privileges haven't ben granted
        elif not self.master:
            return {"status": "access denied", "hint": "Master key is required!"}

        # If "sensor_doc" isn't defined already, crawling database for id
        if sensor_doc is None:

            # Crawling database for sensor with given id
            query = {"id": id}
            sensor_doc = clients_coll.find_one(query)

        # If sensor wasn't found sending "not found" status
        if sensor_doc is None:
            return {"status": "not found"}

        # Getting sensor type from database
        type = sensor_doc["type"]

        # Deleting data according to sensor type
        if type == "co2":
            self.resetCO2(sensor_doc["id"])
        elif type == "person":
            self.resetPerson(sensor_doc["id"])

        return {"status": "ok"}


    def resetCO2(self, id):
        """
        Resets data about the CO2 sensor of given id
        """

        # Getting sensor collection from database
        co2_coll = self.database[CO2_SENSOR_COLLECTION]

        # Deleting data in database if available
        query = {"id": id}
        co2_coll.delete_one(query)



    def resetPerson(self, id):
        """
        Resets data about the person counter of given id
        """

        # Getting sensor collection from database
        person_coll = self.database[PERSON_COUNTER_COLLECTION]

        # Deleting data in database if available
        query = {"id": id}
        person_coll.delete_one(query)

