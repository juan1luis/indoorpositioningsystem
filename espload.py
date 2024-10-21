import network
import urequests
import time

def connect_wifi(ssid, password):
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    sta_if.connect(ssid, password)

    while not sta_if.isconnected():
        time.sleep(1)
    print('Connected to Wi-Fi:', sta_if.ifconfig())

# Scan Wi-Fi networks and send data to the server
def scan_and_send(server_url):
    sta_if = network.WLAN(network.STA_IF)
    networks = sta_if.scan()

    data = {}
    # Manually specify the 3 access points you're tracking
    ap_names = ['S24_ULTRA', 'TP-Link_EA94', 'INFINITUMD29C_2.4']
    
    for net in networks:
        ssid = net[0].decode('utf-8')
        rssi = net[3]
        if ssid in ap_names:
            data[ssid] = {'rssi': rssi}
    print(data)
    try:
        response = urequests.post(server_url, json=data)
        print('Response from server:', response.text)
    except Exception as e:
        print('Error sending data:', e)


# Main loop
connect_wifi('TP-Link_EA94', '**************')
server_url = 'http://192.168.0.105:5000/track'

while True:
    scan_and_send(server_url)
    time.sleep(1)  # Wait 10 seconds before scanning again