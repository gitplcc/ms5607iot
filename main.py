import app_cfg
import MS5607

import machine
import umqtt.simple
import ussl as ssl
import time
import ubinascii

CLIENT_ID = ubinascii.hexlify(machine.unique_id())
TOPIC = b"Chalet Morales/ms5607"

def InitializeSensor():
    bus = machine.I2C(1, scl=machine.Pin(22), sda=machine.Pin(21), freq=400000)
    return MS5607.MS5607(bus)

def Connect2MQTTBroker():
    client = umqtt.simple.MQTTClient(
        CLIENT_ID,
        app_cfg.MQTT_SERVER,
        user=app_cfg.MQTT_USER,
        password=app_cfg.MQTT_PWD,
        keepalive=90,
        ssl=True,
        ssl_params={"cert_reqs": ssl.CERT_NONE},
    )
    client.connect()
    return client

sensor = InitializeSensor()
client = Connect2MQTTBroker()
while True:
    rawp = sensor.getRawPressure()
    rawt = sensor.getRawTemperature()
    msg = f'{{"P": {sensor.toPascals(rawp,rawt)}, "T": {sensor.toCelsiusHundreths(rawt)}}}'
    client.publish(TOPIC, msg.encode('ascii'))
    time.sleep_ms(60_000)
