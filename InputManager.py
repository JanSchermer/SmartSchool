from os import getenv
from time import time

from Mongo import DBClient

# Duration co2 levels remain in database in seconds
CO2_SENSOR_STORE_TIME = int(getenv("SMART_SCHOOL_CO2_STORE_TIME", 604800))

# Database collection names
CLIENTS_COLLECTION = getenv("SMART_SCHOOL_CLIENTS_COLL", "Clients")
PERSON_COUNTER_COLLECTION = getenv("SMART_SCHOOL_PERSON_COLL", "PersonCounters")
CO2_SENSOR_COLLECTION = getenv("SMART_SCHOOL_CO2_COLL", "CO2Sensors")

class InputManager:

    def __init__(self, api:str, db_client:DBClient):
        """
        Creates input manager to manage requests to add data from sensors
        Sets api_valid attribute stating if apiKey is valid

        :param api APIKey send with the request
        :param db_client Database client object
        """

        # Getting database and Clients collection
        self.database = db_client.getDataBase()
        client_coll = self.database[CLIENTS_COLLECTION]

        # Getting data about client
        query = {"key": api}
        api_doc = client_coll.find_one(query) 

        # If client is not available return and set api_available to False
        if api_doc is None:
            self.api_valid = False
            return

        # Saving data from database to variables
        self.api_valid = True
        self.id = api_doc["id"]
        self.type = api_doc["type"]


    def heartbeat(self):
        """
        Updates last heartbeat in database
        """

        # Getting client collection from database
        client_coll = self.database[CLIENTS_COLLECTION]

        # Replacing last heartbeat in database
        query = {"id": self.id}
        replace_data = {"heartbeat": time()}
        client_coll.update(query, {"$set": replace_data})


    def handleRequest(self, json):
        """
        Handles any input request and assesses the type

        :return Boolean if update was successful
        """

        if self.type == "person":
            return self.handlePersonRequest(json)

        elif self.type == "co2":
            return self.handleCO2Request(json)


    def handlePersonRequest(self, json):
        """
        Handles requests from sensors to update person count
        Requires "count" to be a valid integer

        :return Boolean if update was successful
        """

        # Check if request contains valid count
        if(json["count"] is None
                or not isinstance(json["count"], int)):
            return False

        # Get count from request
        count = json["count"]

        # Getting PersonCounter collection from database
        person_coll = self.database[PERSON_COUNTER_COLLECTION]

        # Getting data about this counter from collection
        query = {"id": self.id}
        data = person_coll.find_one(query) 

        # If id is invalid crating new data
        if data is None:

            # Create new collection entry
            data = {"id": self.id, "count": count}
            person_coll.insert(data)
            return True

        # If id is valid increment/decrement count in database
        else:

            # Increment/decrement count
            count = count + data["count"]

            # Updating count in database
            replace_data = {"count": count}
            person_coll.update(query, {"$set": replace_data})

            return True


    def handleCO2Request(self, json):
        """
        Handles requests from sensors to update co2 information
        Requires "co2" to be a valid integer

        :return Boolean if update was successful
        """

        # Check if request contains valid co2 level
        if(json["co2"] is None
                or not isinstance(json["co2"], int)):
            return False

        # Get co2 level from request
        level = {"level": json["co2"], "time": time()}

        # Getting  collection from database
        sensor_coll = self.database[CO2_SENSOR_COLLECTION]

        # Getting data about this sensor from collection
        query = {"id": self.id}
        data = sensor_coll.find_one(query) 

        # If id is invalid create new data
        if data is None:

            # Create new collection entry
            data = {"id": self.id, "levels": [level]}
            sensor_coll.insert(data)

        # If id is valid update database entry
        else:

            # Get levels from database and append new level
            levels = data["levels"]
            levels.append(level)

            # Sorting levels list and removing unnecessary entries
            levels = self.manageCO2Levels(levels)

            # Update levels in database
            replace_data = {"levels": levels}
            sensor_coll.update(query, {"$set": replace_data})

        return True

    def manageCO2Levels(self, levels):
        """
        Takes a list of levels and shrinks the size by removing not needed entries.
        Keeping every entry that's younger then an hour.
        Keeping one entry every 10 minutes for entries of age between an hour and a day.
        Keeping one entry every hour for entries older than a day.

        :return List of necessary to keep levels sorted by age in descending order
        """

        # Creating new level list that will later be returned
        new_levels = []

        # Storing current time for later use
        current_time = time()

        # Iterate threw list and filter expired entries
        filtered = filter(
            lambda entry: entry["time"] > (current_time - CO2_SENSOR_STORE_TIME)
            , levels)

        # Convert filtered results into a list object
        levels = list(filtered)

        # Sorting levels by age in descending order
        levels = sorted(levels, key=lambda entry: entry["time"], reverse=True)

        # Initializing "last_entry" variable so the youngest entry will always be saved
        last_entry = current_time+1

        for level in levels:

            # Calculating age of the entry
            age = current_time - level["time"]

            # No threshold, if entry is younger then one hour
            if age < 60 * 60:
                threshold = 0

            # Threshold of ten minutes, if entry is between one hour and a day old
            elif age < 60 * 60 * 24:
                threshold = 60 * 10

            # Threshold of one hour, if entry is older then a day
            else:
                threshold = 60 * 60

            # Append level to new level list and updating "last_entry",
            # if entry is within the threshold range of the last entry
            if level["time"] + threshold < last_entry:
                new_levels.append(level)
                last_entry = level["time"]

        return new_levels