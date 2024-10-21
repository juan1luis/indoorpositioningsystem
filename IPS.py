from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import math
import pandas as pd


app = Flask(__name__)
socketio = SocketIO(app)

# Known positions of access points (AP1, AP2, AP3)
ACCESS_POINTS = {
    'S24_ULTRA': {'x': 0, 'y': 0, 'tx_power': -35},
    'TP-Link_EA94': {'x': 4.5, 'y': 0, 'tx_power': -44},
    'INFINITUMD29C_2.4': {'x': 2.5, 'y': 5, 'tx_power': -40}
}

#Store RSSI Values
rssi_list = []

class StoreValues:

    def __init__(self, distance, iters) -> None:
        self.distance = distance
        self.iters = iters
        self.saved = False

    def _check_iters(self):

        count = len(rssi_list)
        iters = True if count >= self.iters else False

        if iters and (not self.saved):
            self.save_data()
        else:
            print(f'working --  {count}')
    def storevalue(self, rssi):
        
        if self._check_iters():
            return 
        
        bit = {
            'rssi' : rssi,
            'distance' : self.distance
        }
        rssi_list.append(bit) 

    def save_data(self):
        # Convert the list of dictionaries to a DataFrame
        df = pd.DataFrame(rssi_list)
        
        # Save the DataFrame to a CSV file
        df.to_csv(f'distances_at_{self.distance}m.csv', index=False)
        
        #print(rssi_list)

        self.saved = True
        

storage = StoreValues(1.5, 500)


# Convert RSSI to distance using a simple formula (this needs calibration)
def rssi_to_distance(rssi, tx_power=-50, n=2):
    """
    Convert RSSI to distance (in meters) based on the provided TX power and environmental factor.
    
    Args:
    rssi (float): Received Signal Strength Indicator (RSSI) value.
    tx_power (float): TX power of the router (RSSI at 1 meter), default is -50 dBm.
    n (float): Environmental factor (path loss exponent), default is 2 (free space).
    
    Returns:
    float: Estimated distance (in meters).
    """
    return 10 ** ((tx_power - rssi) / (10 * n))



# Trilateration algorithm to estimate the position
def trilaterate(distances):
    
    x1, y1 = ACCESS_POINTS['S24_ULTRA']['x'], ACCESS_POINTS['S24_ULTRA']['y']
    x2, y2 = ACCESS_POINTS['TP-Link_EA94']['x'], ACCESS_POINTS['TP-Link_EA94']['y']
    x3, y3 = ACCESS_POINTS['INFINITUMD29C_2.4']['x'], ACCESS_POINTS['INFINITUMD29C_2.4']['y']

    r1, r2, r3 = distances['S24_ULTRA'], distances['TP-Link_EA94'], distances['INFINITUMD29C_2.4']

    # Trilateration formula for 2D space (you can use libraries to handle this in 3D)
    A = 2 * x2 - 2 * x1
    B = 2 * y2 - 2 * y1
    C = r1**2 - r2**2 - x1**2 + x2**2 - y1**2 + y2**2
    D = 2 * x3 - 2 * x2
    E = 2 * y3 - 2 * y2
    F = r2**2 - r3**2 - x2**2 + x3**2 - y2**2 + y3**2 

    # Solve for x, y
    x = (C * E - F * B) / (E * A - B * D)
    y = (C * D - A * F) / (B * D - A * E)
    
    return {'x': x, 'y': y}


@app.route('/')
def index():
    return render_template('index.html')


# WebSocket route to receive data from the ESP8266
@app.route('/track', methods=['POST'])
def track_device():
    data = request.json  # Get the JSON data sent by the ESP8266
    
    rssi = data['TP-Link_EA94']['rssi']

    storage.storevalue(rssi)
    try:
        # Assume data contains RSSI from AP1, AP2, AP3
        distances = {ap: rssi_to_distance(rssi['rssi'], ACCESS_POINTS[ap]['tx_power']) for ap, rssi in data.items()}
        
        # Perform trilateration to get position
        position = trilaterate(distances)

        # Send the updated position to the web page via WebSocket
        
        socketio.emit('update_position', position)
        
        return {'status': 'success'}
    except:
        return {'status': 'fail'}



@socketio.on('connect')
def handle_connect():
    print('Client connected')

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
