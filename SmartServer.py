import json

from flask import Flask, request
from os import getenv
from datetime import datetime
import traceback

# Load environment variables
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")

from Mongo import DBClient
from InputManager import InputManager
from OutputManager import OutputManager
from SensorManager import SensorManager
from SSLContextGenerator import generateSSLContext

# Debug mode settings
DEBUG_MODE = getenv("SMART_SCHOOL_DEBUG", False)

# Webserver host and port
PORT = int(getenv("SMART_SCHOOL_PORT", 99))
HOST = getenv("SMART_SCHOOL_HOST", "0.0.0.0")

# MongoDB connection string
DB_CON = getenv("SMART_SCHOOL_DB_CON", "mongodb://localhost:27017/")

# Initialize flask app
app = Flask(__name__, )

# Initialize db client as none
db_client = None

def init():
    global db_client

    # Generating ssl context for webserver
    context = generateSSLContext()

    # Initialize MongoDB Client
    db_client = DBClient(DB_CON)

    # Starting webserver on port 99
    app.run(host=HOST, port=PORT, ssl_context=context, debug=DEBUG_MODE)


def fetchJSON():
    """
    :return JSON data from current request
    """
    return request.get_json()


@app.route("/input", methods=["POST"])
def reciveInput():
    """
    Handle requests from sensors to update data in database.
    Requires json to be send containing "api" as a valid api key.
    """
    try:

        # Fetching JSON data from request
        data = fetchJSON()

        # Initializing input manager with given api key
        input_manager = InputManager(data.get("api"), db_client)

        # Returning "access denied" status, if api key is invalid
        if not input_manager.api_valid:
            return '{"status": "access denied"}', 403

        # Registering heartbeat for the sensor
        input_manager.heartbeat()

        # Passing data to input manager for handling
        successful = input_manager.handleRequest(data)

        # Returning "ok" status, if input manager handled data successfully
        if successful:
            return '{"status": "ok"}', 200

        # Returning "bad request" status, if input manager can't handle data
        else:
            return '{"status": "bad request"}', 400

    except:

        # Printing debug information, if debug mode is enabled
        if DEBUG_MODE:
            printErrorReport()

        # Returning "bad request" status, if any error occurs
        return '{"status": "bad request"}', 400


@app.route("/output", methods=["POST"])
def sendOutput():
    """
    Handle requests from users to get data from database.
    Requires json to be send containing "id" as a valid sensor id.
    """
    try:

        # Fetching JSON data from request
        data = fetchJSON()

        # Initializing output manager with given sensor id and master key if provided
        output_manager = OutputManager(data["id"], db_client, auth=data.get("key"))

        # Returning "not found" status if sensor id is invalid
        if not output_manager.id_valid:
            return '{"status": "not found"}', 404

        # Passing data to output manager for handling
        result = output_manager.handleRequest(data)

        # Dumping dictionary to json string
        result = json.dumps(result)

        return result, 200

    except:

        # Printing debug information, if debug mode is enabled
        if DEBUG_MODE:
            printErrorReport()

        # Returning "bad request" status, if any error occurs
        return '{"status": "bad request"}', 400

@app.route("/sensor", methods=["POST"])
def manageSensor():
    """
    Handle requests from sensors and masters to manage sensors.
    Requires json to be send containing either "id" as a sensor id and "key" as a master key,
    or "api" as an api key.
    Requires json to be send containing "action" as a string containing one of the following actions:
    "create": Creates new sensor, requires field "type" to be set. Response contains "id" and "api", if successful.
    "delete": Deletes sensor of given id.
    "reset": Resets sensor of given id. It's the only action that can be performed using the api key.
    """
    try:

        # Fetching JSON data from request
        data = fetchJSON()

        # Initializing sensor manager with given sensor id and master key if provided
        sensor_manager = SensorManager(db_client, data.get("key"))

        # Getting action from request
        action = data["action"]

        # Initializing response with "bad request" status
        response = {"status": "bad request", "hint": "Invalid action!"}

        # Performing action corresponding to action in request
        if action == "create":
            response = sensor_manager.create(data["type"])

        elif action == "delete":
            response = sensor_manager.destroy(data["id"])

        elif action == "reset":
            response = sensor_manager.reset(data["id"], api=data.get("api"))

        # Initializing response code as 400 (Bad Request)
        response_code = 400

        # Setting response code to 200 if status is "ok"
        if response["status"] == "ok":
            response_code = 200

        # Setting response code to 404 if status is "not found"
        elif response["status"] == "not found":
            response_code = 404

        # Setting response code to 403 if status is "access denied"
        elif response["status"] == "access denied":
            response_code = 403

        # Dumping response to json string
        response = json.dumps(response)

        return response, response_code

    except:

        # Printing debug information, if debug mode is enabled
        if DEBUG_MODE:
            printErrorReport()

        # Returning "bad request" status, if any error occurs
        return '{"status": "bad request"}', 400


def printErrorReport():
    # Getting current time and data
    now = datetime.now()
    time_date = now.strftime("%d.%m.%Y %H:%M:%S")

    # Printing error report to console
    print(f'<<< BEGIN ERROR REPORT FROM SMART SCHOOL SERVER {time_date} >>>')
    print(f'Error while handling request from {request.remote_addr} to {request.url}')
    print(f"Request data: {request.data}\n")
    print(traceback.format_exc())
    print(f'<<< END ERROR REPORT FROM SMART SCHOOL SERVER {time_date} >>>')


# Initializing Smart School Server
if __name__ == '__main__':
    init()