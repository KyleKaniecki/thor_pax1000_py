import time
import ctypes
from ctypes import *

# Load DLL library
lib = cdll.LoadLibrary(
    "C:\\Program Files\\IVI Foundation\\VISA\\Win64\\Bin\\TLPAX_64.dll"
)


class Polarimeter:

    def __init__(
        self, measurement_mode: int = 9, wavelength: float = 785e-9, scan_rate: int = 60
    ):
        self.handle = c_ulong()
        self.resource = c_char_p(b"")
        self.device_count = c_int()

        self.measurement_mode = measurement_mode
        self.wavelength = wavelength
        self.scan_rate = scan_rate

    def init(self):
        # Detect and initialize PAX1000 device
        IDQuery = True
        resetDevice = False

        # Check how many PAX1000 are connected
        lib.TLPAX_findRsrc(self.handle, byref(self.device_count))
        if self.device_count.value < 1:
            print("No PAX1000 device found.")
            self.exit()
        else:
            print(self.device_count.value, "PAX1000 device(s) found.")
            print("")

        # Connect to the first available PAX1000
        lib.TLPAX_getRsrcName(self.handle, 0, self.resource)
        if 0 == lib.TLPAX_init(
            self.resource.value, IDQuery, resetDevice, byref(self.handle)
        ):
            print("Connection to first PAX1000 initialized.")
        else:
            print("Error with initialization.")
            self.exit()
        print("")

        # Short break to make sure the device is correctly initialized
        time.sleep(2)

        # Make settings
        lib.TLPAX_setMeasurementMode(self.handle, self.measurement_mode)
        lib.TLPAX_setWavelength(self.handle, c_double(self.wavelength))
        lib.TLPAX_setBasicScanRate(self.handle, c_double(self.scan_rate))

        # Short break
        time.sleep(2)

    def close(self):
        # Close
        lib.TLPAX_close(self.handle)
        print("Connection to PAX1000 closed.")

    def exit(self):
        self.close()
        exit()

    def print_current_settings(self):
        wavelength = c_double()
        lib.TLPAX_getWavelength(self.handle, byref(wavelength))
        print("Set wavelength [nm]: ", wavelength.value * 1e9)

        mode = c_int()
        lib.TLPAX_getMeasurementMode(self.handle, byref(mode))
        print("Set mode: ", mode.value)

        scanrate = c_double()
        lib.TLPAX_getBasicScanRate(self.handle, byref(scanrate))
        print("Set scanrate: ", scanrate.value)

        print("")

    def take_measurement(self):
        scanID = c_int()
        lib.TLPAX_getLatestScan(self.handle, byref(scanID))

        azimuth = c_double()
        ellipticity = c_double()
        lib.TLPAX_getPolarization(
            self.handle, scanID.value, byref(azimuth), byref(ellipticity)
        )

        s1 = c_double()
        s2 = c_double()
        s3 = c_double()
        lib.TLPAX_getStokes(self.handle, scanID.value, byref(s1), byref(s2), byref(s3))

        power = c_double()
        powerPolarized = c_double()
        powerUnpolarized = c_double()
        lib.TLPAX_getPower(
            self.handle,
            scanID.value,
            byref(power),
            byref(powerPolarized),
            byref(powerUnpolarized),
        )

        dop = c_double()
        dolp = c_double()
        docp = c_double()
        lib.TLPAX_getDOP(
            self.handle, scanID.value, byref(dop), byref(dolp), byref(docp)
        )

        # Release this scan
        lib.TLPAX_releaseScan(self.handle, scanID)

        return {
            "azimuth": azimuth.value,
            "ellipticity": ellipticity.value,
            "s1": s1.value,
            "s2": s2.value,
            "s3": s3.value,
            "power": {
                "raw": power.value,
                "polarized": powerPolarized.value,
                "unpolarized": powerUnpolarized.value,
            },
            "dop": dop.value,
            "dolp": dolp.value,
            "docp": docp.value,
        }

    def __enter__(self):
        self.init()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
