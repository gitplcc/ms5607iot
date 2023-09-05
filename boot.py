import app_cfg

import network
import ntptime
import time


def connect2wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)
    keep_on = True
    while keep_on:
        wlan.active(True)
        while not wlan.active():
            time.sleep_ms(100)
        nets = sorted(wlan.scan(), key=lambda net: net[3], reverse=True)
        ssids = [i[0] for i in nets]
        if any((ssid := net) in ssids for net in app_cfg.WIFI_TOKENS.keys()):
            print(ssid, app_cfg.WIFI_TOKENS[ssid])
            wlan.config(reconnects=3)
            wlan.connect(ssid, app_cfg.WIFI_TOKENS[ssid])
            while wlan.status() == network.STAT_CONNECTING:
                time.sleep_ms(100)
            if wlan.isconnected():
                return wlan

        if keep_on:
            wlan.active(False)
            time.sleep_ms(10_000)

    return None


wlan = connect2wifi()
ntptime.settime()
