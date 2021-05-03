import functools
import time
from debugging import Timer

def timer(func):
    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        t0 = perf_counter_ns()
        value = func(*args, **kwargs)
        t1 = perf_counter_ns()
        elapsed_time = t1 - t0
        print(f"Elapsed time: {elapsed_time/10**6:.3f} ms")
        return value
    return wrapper_timer

def debug(func):
    """Print arguments and return value"""
    @functools.wraps(func)
    def wrapper_debug(*args, **kwargs):
        args_repr = [repr(a) for a in args]                      # 1
        kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]  # 2
        signature = ", ".join(args_repr + kwargs_repr)           # 3
        print(f"Calling {func.__name__}({signature})")
        value = func(*args, **kwargs)
        print(f"{func.__name__!r} returned {value!r}")           # 4
        return value
    return wrapper_debug

'''
1. Create a list of the positional arguments. Use repr() to get a nice string representing each argument.
2. Create a list of the keyword arguments. The f-string formats each argument as key=value where the !r specifier means that repr() is used to represent the value.
3. The lists of positional and keyword arguments is joined together to one signature string with each argument separated by a comma.
4. The return value is printed after the function is executed.
'''
@Timer(name="setup_device", units="ms")
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

MQTT_CLIENT_ID = 'pi'
MQTT_SUB_TOPIC = []
SUBLVL1 = 'nred2' + MQTT_CLIENT_ID
MQTT_REGEX = SUBLVL1 + '/([^/]+)/([^/]+)'
MQTT_PUB_TOPIC = ['pi2nred/', '/' + MQTT_CLIENT_ID]
deviceD = {}

device = "ina219A"  
lvl2 = "ina219A"
data_keys = ['Vbusf', 'IbusAf', 'PowerWf']
setup_device(device, lvl2, data_keys)