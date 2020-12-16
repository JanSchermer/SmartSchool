from os import getenv
from time import time

from Mongo import DBClient

# Database collection names
MASTERS_COLLECTION = getenv("SMART_SCHOOL_MASTERS_COLL", "Masters")
CLIENTS_COLLECTION = getenv("SMART_SCHOOL_CLIENTS_COLL", "Clients")
PERSON_COUNTER_COLLECTION = getenv("SMART_SCHOOL_PERSON_COLL", "PersonCounters")
CO2_SENSOR_COLLECTION = getenv("SMART_SCHOOL_CO2_COLL", "CO2Sensors")

class OutputManager:

    def __init__(self, id:str, db_client:DBClient, auth:str=None):
        """
        Creates output manager to manage requests from users to get sensor data
        Sets "id_valid" attribute stating if id is valid

        :param id Id of the requested sensor
        :param db_client Database client object
        :param auth Authentication key to get additional information with master privileges
        """

        # Initializing id and master attributes
        self.id = id
        self.master = False

        # Getting database object from client
        self.database = db_client.getDataBase()

        # If auth is provided, trying to grant master privileges
        if auth is not None:
            self.check_auth(auth)

        # Fetching basic sensor information from database
        self.fetchInformation()


    def fetchInformation(self):
        """
        Checking id and fetching information about sensor and saving it to the current object.
        Sets "id_valid" attribute based on the id being valid.
        Sets "type" and "last_heartbeat" attribute based on database data.
        Sets "online" attribute based on the last heartbeat being less then 2 minutes ago.
        Sets "api_key" attribute if master privileges are granted.
        If id is invalid "id_valid" is the only attribute being set.

        :return Boolean if id is valid
        """

        # Getting clients collection from database
        clients_coll = self.database[CLIENTS_COLLECTION]

        # Crawling collection for given sensor id
        query = {"id": self.id}
        sensor_doc = clients_coll.find_one(query) 

        # Checking if id is valid and returning, if it's invalid
        self.id_valid = sensor_doc is not None
        if not self.id_valid:
            return False

        # Saving information about sensor
        self.type = sensor_doc["type"]
        self.last_heartbeat = sensor_doc["heartbeat"]

        # Setting sensors online status based on it's last heartbeat being less then 2 minutes ago
        self.online = time() - self.last_heartbeat < 2 * 60

        # Getting api key of sensor, if master privileges are granted
        if self.master:
            self.api_key = sensor_doc["key"]

        return True


    def check_auth(self, key):
        """
        Checks authentication key for master privileges and grants them, if key is valid
        """

        # Getting masters collection from database
        masters_coll = self.database[MASTERS_COLLECTION]

        # Crawling collection for objects with given authentication key
        query = {"key": key}
        if masters_coll.count_documents(query) > 0:

            # Granting master privileges, if key was found
            self.master = True
            return True

        return False


    def generateBasicResponse(self) -> dict:
        """
        Generates basic response object with read in sensor information.
        Information returned by this function is never sensor type specific information.
        """

        # Creating basic response
        response = {
                "status": "ok",
                "id": self.id,
                "heartbeat": self.last_heartbeat,
                "online": self.online,
                "master": self.master
               }

        # Appending api key, if master privileges have been granted
        if self.master:
            response["key"] = self.api_key

        return response


    def handleRequest(self, json):
        """
        Handles request and returns requested information as a dictionary.
        Response contains "status" that will always be "ok" if no errors occur.
        Response contains "id" that will always be the same as the requested id as a string.
        Response contains "heartbeat" that is set to the time seconds of the last heartbeat as a double.
        Response contains "master" stating if master privileges have been granted as a boolean.
        Response contains "key" that will be the api key of the sensor as a string.
        The api key will only be appended, if master privileges have been granted.

        Only CO2Sensor:
        Response contains "levels" containing all stored levels as a list of dictionaries containing
            "time" set to time seconds the measurement occurred as a double and
            "level" set to the measured co2 level as an integer

        Only Person Counter:
        Response contains "count" set to the count of people stored in the database

        :return Dict containing all information listed above
        """

        if self.type == "person":
            return self.handlePersonRequest()

        elif self.type == "co2":
            return self.handleCO2Request()


    def handleCO2Request(self):
        """
        Handles requests for CO2 sensors an generates response.
        Generates basic sensor information and appends CO2 sensor specific information
        """

        # Generating default response with basic data about the sensor
        response = self.generateBasicResponse()

        # Getting co2 sensor collection from database
        co2_coll = self.database[CO2_SENSOR_COLLECTION]

        # Crawling database for sensor document
        query = {"id": self.id}
        sensor_doc = co2_coll.find_one(query) 

        # Setting "levels" to an empty list, if the sensor isn't initialized in the database yet
        if sensor_doc is None:
            response["levels"] = []

        # Setting "levels" to the levels stored in the database, if available
        else:
            response["levels"] = sensor_doc["levels"]

        return response


    def handlePersonRequest(self):
        """
        Handles requests for person counters an generates response.
        Generates basic sensor information and appends person counter specific information
        """

        # Generating default response with basic data about the sensor
        response = self.generateBasicResponse()

        # Getting person counter collection from database
        person_coll = self.database[PERSON_COUNTER_COLLECTION]

        # Crawling database for sensor document
        query = {"id": self.id}
        sensor_doc = person_coll.find_one(query) 

        # Setting "count" to 0, if the counter isn't initialized in the database yet
        if sensor_doc is None:
            response["count"] = 0

        # Setting "count" to the count stored in the database, if available
        else:
            response["count"] = sensor_doc["count"]

        return response

