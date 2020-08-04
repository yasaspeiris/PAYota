##IOTA
# Imports the PyOTA library
from iota import Iota
from iota import Address

# Function for checking address balance on the IOTA tangle. 
def checkbalance():

    print("Checking balance")
    gb_result = api.get_balances(address)
    balance = gb_result['balances']
    return (balance[0])

# URL to IOTA fullnode used when checking balance
iotaNode = "https://nodes.thetangle.org:443"

# Create an IOTA object
api = Iota(iotaNode, "")

# IOTA address to be checked for new light funds 
# IOTA addresses can be created using the IOTA Wallet
address = [Address(b'LMXNOWTOHIRSFFTJVIYYFOVG9LRPNKWSFZOBTNLKBQYDRANWURGMHSMAHPAAPDFGPWAERP9XJRFCCZMAWVYMDBBEZD')]

# Get current address balance at startup and use as baseline for measuring new funds being added.   
startingbalance = checkbalance()
devicestatus = False


##MODBUS 
import minimalmodbus

instrument = minimalmodbus.Instrument('/dev/ttyUSB0', 1, mode = 'rtu') # port name, slave address - Use multiple objects to talk with multiple power meters
instrument.serial.baudrate = 9600

import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(4,GPIO.OUT)
GPIO.output(4,GPIO.HIGH)


prev_voltage = 0
prev_current = 0
prev_energy = 0
prev_power = 0

##Flask and SocketIO

from threading import Lock
from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect

async_mode = None

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()


def background_thread():
    global startingbalance
    balchecker = 0
    count = 0
    deviceBalance = 0
    currentbalance = 0
    usedenergy = 0
    firstflag = True
    while True:
        # Check for new funds and add to lightbalance when found.
        if balchecker == 10:
            currentbalance = checkbalance()
            if currentbalance > startingbalance : 
                deviceBalance = currentbalance - startingbalance
                startingbalance = currentbalance
            balchecker = 0

        balchecker = balchecker + 1

        if(deviceBalance > 0) :
            
            if devicestatus == False:
                print("device ON")
                GPIO.output(4,GPIO.LOW)
                devicestatus=True
                for i in range (0,10):
                    startingenergy = get_energy()
                    socketio.sleep(0.5)
            
            newnenergy = get_energy()

            usedenergy = newnenergy - startingenergy
            deviceBalance = deviceBalance - usedenergy 
            if deviceBalance <0 :
                deviceBalance = 0
            socketio.emit('my_response',
                        {'iotabalance': deviceBalance, 'current' : get_current(), 'power' :get_power() , 'energy' :usedenergy},
                        namespace='/test')

        else :
            print("device OFF")
            deviceBalance = 0
            GPIO.output(4,GPIO.HIGH)
            devicestatus=False
            socketio.emit('my_response',
                        {'iotabalance': deviceBalance, 'current' : 0, 'power' : 0, 'energy' :usedenergy},
                        namespace='/test')



@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)


@socketio.on('connect', namespace='/test')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)
    emit('my_response', {'iotabalance': 0, 'current' : 0, 'power' :0 , 'energy' :0})


@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected', request.sid)



#######################################################################

def get_energy():
    global prev_energy
    try:
        energy_low = instrument.read_register(0x0005, numberOfDecimals=0, functioncode=4, signed=False)
        energy_high = instrument.read_register(0x0006, numberOfDecimals=0, functioncode=4, signed=False)
        energy = (energy_high << 8 | energy_low)
        prev_energy = energy
        return energy
    except ValueError:
        return prev_energy
    except IOError:
        return prev_energy

def get_power():
    global prev_power
    try:
        power_low = instrument.read_register(0x0003, numberOfDecimals=0, functioncode=4, signed=False)
        power_high = instrument.read_register(0x0004, numberOfDecimals=0, functioncode=4, signed=False)
        power = (power_high << 8 | power_low)/10.0
        prev_power = power
        return power
    except ValueError:
        return prev_power
    except IOError:
        return prev_power

def get_current():
    global prev_current
    try:
        current_low = instrument.read_register(0x0001, numberOfDecimals=0, functioncode=4, signed=False)
        current_high = instrument.read_register(0x0002, numberOfDecimals=0, functioncode=4, signed=False)
        current = (current_high << 8 | current_low)/1000.0
        prev_current = current
        return current
    except ValueError:
        return prev_current
    except IOError:
        return prev_current


if __name__ == '__main__':
    socketio.run(app,host = '192.168.8.106', port = 4500, debug=True)
