import sys, json, logging, re
from time import sleep, perf_counter
import paho.mqtt.client as mqtt
from os import path
from pathlib import Path
from logging.handlers import RotatingFileHandler

def setup_logging(log_dir, log_level=logging.INFO, mode=1):
    # Create loggers
    # INFO + mode 1  = info           print only
    # INFO + mode 2  = info           print+logfile output
    # DEBUG + mode 1 = info and debug print only
    # DEBUG + mode 2 = info and debug print+logfile output

    if mode == 1:
        logfile_log_level = logging.CRITICAL
    elif mode == 2:
        logfile_log_level = logging.DEBUG

    main_logger = logging.getLogger(__name__)
    main_logger.setLevel(log_level)
    log_file_format = logging.Formatter("[%(levelname)s] - %(asctime)s - %(name)s - : %(message)s in %(pathname)s:%(lineno)d")
    log_console_format = logging.Formatter("[%(levelname)s]: %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.CRITICAL)
    console_handler.setFormatter(log_console_format)

    exp_file_handler = RotatingFileHandler('{}/exp_debug.log'.format(log_dir), maxBytes=10**6, backupCount=5) # 1MB file
    exp_file_handler.setLevel(logfile_log_level)
    exp_file_handler.setFormatter(log_file_format)

    exp_errors_file_handler = RotatingFileHandler('{}/exp_error.log'.format(log_dir), maxBytes=10**6, backupCount=5)
    exp_errors_file_handler.setLevel(logging.WARNING)
    exp_errors_file_handler.setFormatter(log_file_format)

    main_logger.addHandler(console_handler)
    main_logger.addHandler(exp_file_handler)
    main_logger.addHandler(exp_errors_file_handler)
    return main_logger

def on_connect(client, userdata, flags, rc):
    """ on connect callback verifies a connection established and subscribe to TOPICs"""
    global MQTT_SUB_TOPIC
    logging.info("attempting on_connect")
    if rc==0:
        mqtt_client.connected = True
        for topic in MQTT_SUB_TOPIC:
            client.subscribe(topic)
            logging.info("Subscribed to: {0}\n".format(topic))
        logging.info("Successful Connection: {0}".format(str(rc)))
    else:
        mqtt_client.failed_connection = True  # If rc != 0 then failed to connect. Set flag to stop mqtt loop
        logging.info("Unsuccessful Connection - Code {0}".format(str(rc)))

def on_message(client, userdata, msg):
    """on message callback will receive messages from the server/broker. Must be subscribed to the topic in on_connect"""
    logging.debug("Received: {0} with payload: {1}".format(msg.topic, str(msg.payload)))

def on_publish(client, userdata, mid):
    """on publish will send data to client"""
    #Debugging. Will unpack the dictionary and then the converted JSON payload
    #logging.debug("msg ID: " + str(mid)) 
    #logging.debug("Publish: Unpack outgoing dictionary (Will convert dictionary->JSON)")
    #for key, value in outgoingD.items():
    #    logging.debug("{0}:{1}".format(key, value))
    #logging.debug("Converted msg published on topic: {0} with JSON payload: {1}\n".format(MQTT_PUB_TOPIC1, json.dumps(outgoingD))) # Uncomment for debugging. Will print the JSON incoming msg
    pass 

def on_disconnect(client, userdata,rc=0):
    logging.debug("DisConnected result code "+str(rc))
    mqtt_client.loop_stop()

def mqtt_setup(IPaddress):
    global MQTT_SERVER, MQTT_CLIENT_ID, MQTT_USER, MQTT_PASSWORD, MQTT_SUB_TOPIC, MQTT_PUB_TOPIC, SUBLVL1, MQTT_REGEX
    global mqtt_client
    home = str(Path.home())                       # Import mqtt and wifi info. Remove if hard coding in python script
    with open(path.join(home, "stem"),"r") as f:
        user_info = f.read().splitlines()
    MQTT_SERVER = IPaddress                    # Replace with IP address of device running mqtt server/broker
    MQTT_USER = user_info[0]                   # Replace with your mqtt user ID
    MQTT_PASSWORD = user_info[1]               # Replace with your mqtt password
    # SUBSCRIBE: Specific MQTT_SUB_TOPICS created inside 'setup_device' function
    MQTT_SUB_TOPIC = []
    SUBLVL1 = 'nred2' + MQTT_CLIENT_ID
    # PUBLISH: Specific MQTT_PUB_TOPICS created at time of publishing using string.join
    MQTT_PUB_TOPIC = ['pi2nred/', '/' + MQTT_CLIENT_ID]
    # MQTT STRUCTURE - TOPIC/PAYLOAD
    # TOPIC levels --> lvl1/lvl2/lvl3
    # PAYLOAD contains the data (JSON string represinting python/js object with key:value is best format
    #                            but can also be simple int, str, boolean)
    #
    # MQTT_SUBSCRIBE_TOPIC FORMAT
    # lvl1 = 'nred2' + MQTT_CLIENT -- From nodered to machine. machine can be generic or unique/specific
    # lvl2 = 'device function'     -- Example servoZCMD, stepperZCMD
    # lvl3 = free form             -- Example controls (stepper controls); 0,1,2 (specific servo)
    #
    # MQTT_PUBLISH_TOPIC FORMAT
    # lvl1 = 'pi2nred'|'esp2nred'  -- From machine to nodered. (generic machine)
    # lvl2 = 'device' sending data -- Device examples, adc, ina219, rotary encoder, stepper
    #        'deviceA'|'deviceB'      Device can be generic or specific. this is updated in 'create_device' functions
    #        'nredZCMD'               May also be machine sending command to nred to update dashboard
    # lvl3 = free form             -- May be specific machine (MQTT_CLIENT_ID) or general command
    #
    # MQTT PAYLOAD CONVERSIONS
    # Simple commands/data sent with integer, boolean, string, list payloads
    # Complex commands/data payloads sent with JSON format using python dict/js object notation (key:value)
    #  mach2nred
    #   PYTHON(publish)  -- Convert from python_object to JSON string/payload [json.dumps(python_object) --> JSON_msg.payload ]
    #   NODERED(mqtt_in) -- Convert from JSON string/payload to js_object     [JSON.parse(JSON_msg.payload) --> js_object     ] 
    #                       js_object named 'fields' to align with influxdb naming (values accessed with fields[key]=value or fields.key=value)
    #  nred2mach
    #   NODERED(mqtt_out)  -- mqtt_out: Keep node red data in js_object format (fields[key]=value)
    #   PYTHON(on_message) -- Convert JSON string payload to python_object    [python_object <-- json.loads(msg.payload.decode)]
    #
    # MSG PAYLOAD KEY:VALUE FORMAT  (script is demoMQTT.py, module is lib/Module.py)
    #  STEPS -- synchronize python dict keys with NodeRed js object keys using 'mqtt_payload_keys'
    #   1 - Define mqtt_payload_keys (key labels for python/js objects) in python script 'create_device' functions
    #       mqtt_payload_keys is then passed to the device module as an argument
    #   2 - Design device module so the 'outgoing' data will be a dictionary using the mqtt_payload_key names
    #   3 - Have Python script retrieve 'outgoing' data (dict) from device and publish using mqtt_payload_key names
    #   4 - NodeRed JSON.parse function will convert msg.payload ('outgoing') to js_object
    #        mqtt_payload_key names are used to create js_object (fields) keys
    #        fields/js_object items can be used in node red dashboard using fields.key (in nodered will be payload[0].key)
    #
    # NODE-RED BACKGROUND
    #  Topic/payload format tries to align with influxdb (TAGS/FIELDS) to make writing to database easy
    #  Topic levels are converted to TAGS inside NodeRed
    #  JSON string is used to construct js_object with FIELDS (fields[key]=value) 
    # The NodeRed msg.payload then becomes an array containing [FIELDS, TAGS]
    # Final NodeRed payload: fields[key]  data is accessed with msg.payload[0].key
    #                        tags(topic levels) are access with msg.payload[1].lvlx (lvl1, lvl2, lvl3)
    
    MQTT_SUB_TOPIC = []

    SUBLVL1 = 'nred2' + MQTT_CLIENT_ID

    # lvl2: Specific MQTT_PUB_TOPICS created at time of publishing done using string.join (specifically item.join)
    MQTT_PUB_TOPIC = ['pi2nred/', '/' + MQTT_CLIENT_ID]

    mqtt_outgoingD = {}            # Container for data to be published via mqtt
    device = []                    # mqtt lvl2 topic category and '.appended' in create functions

def setup_device(device, lvl2, data_keys):
    global deviceD, SUBLVL1
    if deviceD.get(device) == None:
        deviceD[device] = {}
        deviceD[device]['data'] = {}
        deviceD[device]['lvl2'] = lvl2 # Sub/Pub lvl2 in topics. Does not have to be unique, can piggy-back on another device lvl2
        topic = f"{SUBLVL1}/{deviceD[device]['lvl2']}ZCMD/+"
        if topic not in MQTT_SUB_TOPIC:
            MQTT_SUB_TOPIC.append(topic)
            for key in data_keys:
                deviceD[device]['data'][key] = 0
        else:
            for key in data_keys:
                for item in deviceD:
                    if deviceD[item]['data'].get(key) != None:
                        print(f'**DUPLICATE WARNING {device} and {item} are both publishing {key} on {topic}')
                deviceD[device]['data'][key] = 0
        deviceD[device]['send'] = False
        print('\n{0} Subscribing to: {1}'.format(device, topic))
        print('   JSON payload keys will be:{0}'.format([*deviceD[device]['data']]))
    else:
        sys.exit(f'Device {device} already in use. Device name should be unique')

def main():
    global deviceD      # Containers setup in 'create' functions and used for Publishing mqtt
    global MQTT_SERVER, MQTT_USER, MQTT_PASSWORD, MQTT_CLIENT_ID, mqtt_client, MQTT_PUB_TOPIC
    global logger, logger_log_level

    # Set next 3 variables for different logging options
    logger_log_level= logging.DEBUG # CRITICAL=logging off. DEBUG=get variables. INFO=status messages.
    logger_setup = 1  # 0 for basicConfig, 1 for custom logger with RotatingFileHandler (RFH)
    RFHmode = 2 # If logger_setup ==1 (RotatingFileHandler) then access to modes below
                #Arguments
                #log_level, RFHmode|  logger.x() | output
                #------------------|-------------|-----------
                #      INFO, 1     |  info       | print only
                #      INFO, 2     |  info       | print+logfile
                #      DEBUG,1     |  info+debug | print only
                #      DEBUG,2     |  info+debug | print+logfile
    if logger_setup == 0:
        if len(logging.getLogger().handlers) == 0:      # Root logger does not already exist, will create it
            logging.basicConfig(level=logger_log_level) # Create Root logger
            logger = logging.getLogger(__name__)        # Set logger to root logging
            logger.setLevel(logger_log_level)
        else:
            logger = logging.getLogger(__name__)        # Root logger already exists so just linking logger to it
            logger.setLevel(logger_log_level)
    elif logger_setup == 1:                             # Using custom logger with RotatingFileHandler
        logger = setup_logging(path.dirname(path.abspath(__file__)), logger_log_level, RFHmode ) # dir for creating logfile
    logger.info(logger)

    MQTT_CLIENT_ID = 'pi' # Can make ID unique if multiple Pi's could be running similar devices (ie servos, ADC's) 
                          # Node red will need mqtt_in topic linked to unique MQTT_CLIENT_ID
    mqtt_setup('10.0.0.115')
    
    deviceD = {}  # Primary container for storing all devices, topics, and data
                  # Device name should be unique, can not duplicate device ID
                  # Topic lvl2 name can be a duplicate, meaning multipple devices publishing data on the same topic
                  # If topic lvl2 name repeats would likely want the data_keys to be unique
    
    ina219Set = {}

    device = "ina219A"  
    lvl2 = "ina219A"
    data_keys = ['Vbusf', 'IbusAf', 'PowerWf']
    setup_device(device, lvl2, data_keys)
    ina219Set[device] = piina219.PiINA219(*data_keys, gainmode="auto", maxA=0.4, address=0x40, mlogger=logger, mlog_level=logger_log_level)

    logger.info("\n")

    #==== START/BIND MQTT FUNCTIONS ====#
    # Create a couple flags to handle a failed attempt at connecting. If user/password is wrong we want to stop the loop.
    mqtt.Client.connected = False             # Flag for initial connection (different than mqtt.Client.is_connected)
    mqtt.Client.failed_connection = False     # Flag for failed initial connection
    # Create our mqtt_client object and bind/link to our callback functions
    mqtt_client = mqtt.Client(MQTT_CLIENT_ID) # Create mqtt_client object
    mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD) # Need user/password to connect to broker
    mqtt_client.on_connect = on_connect       # Bind on connect
    mqtt_client.on_disconnect = on_disconnect # Bind on disconnect
    mqtt_client.on_message = on_message       # Bind on message
    mqtt_client.on_publish = on_publish       # Bind on publish
    logging.info("Connecting to: {0}".format(MQTT_SERVER))
    mqtt_client.connect(MQTT_SERVER, 1883)    # Connect to mqtt broker. This is a blocking function. Script will stop while connecting.
    mqtt_client.loop_start()                  # Start monitoring loop as asynchronous. Starts a new thread and will process incoming/outgoing messages.
    # Monitor if we're in process of connecting or if the connection failed
    while not mqtt_client.connected and not mqtt_client.failed_connection:
        logging.info("Waiting")
        sleep(1)
    if mqtt_client.failed_connection:         # If connection failed then stop the loop and main program. Use the rc code to trouble shoot
        mqtt_client.loop_stop()
        sys.exit()
    
    #==== MAIN LOOP ====================#
    # MQTT setup is successful. Initialize dictionaries and start the main loop.   
    t0_sec = perf_counter() # sec Counter for getting stepper data. Future feature - update interval in  node-red dashboard to link to perf_counter
    msginterval = 1       # Adjust interval to increase/decrease number of mqtt updates.
    try:
        while True:
            if (perf_counter() - t0_sec) > msginterval: # Get data on a time interval
                for device, ina219 in ina219Set.items():
                    deviceD[device]['data'] = ina219.read()
                    mqtt_client.publish(deviceD[device]['lvl2'].join(MQTT_PUB_TOPIC), json.dumps(deviceD[device]['data']))  # publish voltage values
                t0_sec = perf_counter()
    except KeyboardInterrupt:
        logging.info("Pressed ctrl-C")
    finally:
        logging.info("Exiting")

if __name__ == "__main__":
    main()