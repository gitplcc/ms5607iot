import time


class MS5607:
    """
    http://www.parallaxinc.com/sites/default/files/downloads/29124-APPNote_520_C_code.pdf
    http://www.parallaxinc.com/sites/default/files/downloads/29124-MS5607-02BA03-Datasheet.pdf
    Offset for humidity to provide better precision
    """

    OVSF_256 = 0x00
    OVSF_512 = 0x02
    OVSF_1024 = 0x04
    OVSF_2048 = 0x06
    OVSF_4096 = 0x08

    DEVICE_ADDRESS = 0x76
    _CMD_RESET = 0x1E
    _CMD_ADC_D1 = 0x40
    _CMD_ADC_D2 = 0x50
    _CMD_ADC_READ = 0x00
    _CMD_PROM_RD = 0xA0

    def __init__(self, bus):
        self._bus = bus
        self.highPrecission = False
        self.oversampling = self.OVSF_4096
        self.resetSensor()
        self._coefficients = self.readCoefficients()

    # Some utility methods
    def _readADC(self):
        self._bus.writeto(self.DEVICE_ADDRESS, self._CMD_ADC_READ.to_bytes(1, "big"))
        bytes = self._bus.readfrom(self.DEVICE_ADDRESS, 3)
        return (bytes[0] << 16) + (bytes[1] << 8) + bytes[2]

    def _readCoefficient(self, i):
        cmd = (self._CMD_PROM_RD + (i << 1)).to_bytes(1, "big")
        self._bus.writeto(self.DEVICE_ADDRESS, cmd)
        bytes = self._bus.readfrom(self.DEVICE_ADDRESS, 2)
        return (bytes[0] << 8) + (bytes[1])

    def _takeSample(self, cmd):
        # set conversion mode
        self._bus.writeto(
            self.DEVICE_ADDRESS, (cmd | self.oversampling).to_bytes(1, "big")
        )
        sleepTime = {
            self.OVSF_256: 900,
            self.OVSF_512: 3_000,
            self.OVSF_1024: 4_000,
            self.OVSF_2048: 6_000,
            self.OVSF_4096: 10_000,
        }
        time.sleep_us(sleepTime[self.oversampling])
        return self._readADC()

    # Commands
    def resetSensor(self):
        self._bus.writeto(self.DEVICE_ADDRESS, self._CMD_RESET.to_bytes(1, "big"))
        time.sleep_us(3000)  # wait for the reset sequence timing

    def readCoefficients(self):
        coefficients = [0] * 8
        for i in range(8):
            coefficients[i] = self._readCoefficient(i)
        return coefficients

    def getRawPressure(self):
        return self._takeSample(self._CMD_ADC_D1)

    def getRawTemperature(self):
        return self._takeSample(self._CMD_ADC_D2)

    def toCelsiusHundreths(self, rawT):
        dT = rawT - (self._coefficients[5] << 8)
        temp = 2000 + (dT * self._coefficients[6] >> 23)
        if self.highPrecission and temp < 2000:
            t2 = dT * dT >> 31
            temp = temp - t2
        return temp

    def toPascals(self, rawP, rawT):
        # Calculate 1st order pressure and temperature
        dT = rawT - (self._coefficients[5] << 8)
        # Offset at actual temperature
        off = (self._coefficients[2] << 17) + (self._coefficients[4] * dT >> 6)
        # Sensitivity at actual temperature
        sens = (self._coefficients[1] << 16) + (self._coefficients[3] * dT >> 7)
        if self.highPrecission:
            temp = 2000 + (dT * self._coefficients[6] >> 23)
            if temp < 2000:
                dT2 = (temp - 2000) ** 2
                off2 = 61 * dT2 >> 4
                sens2 = dT2 << 1
                if temp < -1500:
                    dT2 = (temp + 1500) ** 2
                    off2 = off2 + 15 * dT2
                    sens2 = sens2 + dT2 << 3
                off = off - off2
                sens = sens - sens2
        # Temperature compensated pressure
        return (rawP * sens >> 21) - off >> 15
