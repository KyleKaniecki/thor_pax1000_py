import time
import ctypes
from ctypes import *
from datetime import datetime, timezone

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

        self.latest_scan_id = 255

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

    def read_scans(self) -> list[dict]:
        scans = []
        for i in range(int(self.latest_scan_id), 255, -1):
            scans.append(self.read_measurement(i))

        return scans

    def release_scans(self):
        # Release this instance's scans
        for i in range(int(self.lastestScanID), 255, -1):
            lib.TLPAX_releaseScan(self.handle, c_int(i))

        self.latest_scan_id = 255

    def close(self):
        self.release_scans()
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
        self.latest_scan_id = int(scanID.value)

    def read_measurement(self, id) -> dict:
        scan_id = c_int(id)

        azimuth = c_double()
        ellipticity = c_double()
        lib.TLPAX_getPolarization(
            self.handle, scan_id, byref(azimuth), byref(ellipticity)
        )

        s1 = c_double()
        s2 = c_double()
        s3 = c_double()
        lib.TLPAX_getStokes(self.handle, scan_id, byref(s1), byref(s2), byref(s3))

        power = c_double()
        powerPolarized = c_double()
        powerUnpolarized = c_double()
        lib.TLPAX_getPower(
            self.handle,
            scan_id,
            byref(power),
            byref(powerPolarized),
            byref(powerUnpolarized),
        )

        dop = c_double()
        dolp = c_double()
        docp = c_double()
        lib.TLPAX_getDOP(self.handle, scan_id, byref(dop), byref(dolp), byref(docp))

        return {
            "ts": int(datetime.now(timezone.utc).timestamp()),
            "azimuth": float(azimuth.value),
            "ellipticity": float(ellipticity.value),
            "s1": float(s1.value),
            "s2": float(s2.value),
            "s3": float(s3.value),
            "power": float(power.value),
            "power_polarized": float(powerPolarized.value),
            "power_unpolarized": float(powerUnpolarized.value),
            "dop": float(dop.value),
            "dolp": float(dolp.value),
            "docp": float(docp.value),
        }

    def __enter__(self):
        self.init()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
