#!/usr/bin/env python3
"""
State of Charge (SoC) Estimator via Coulomb Counting
======================================================
Target Hardware : Raspberry Pi (any model with I2C)
Current Sensor  : INA219 (I2C, address 0x40 by default)
Battery         : Xeanerol 12V 2600mAh Li-ion pack
                  (3S Li-ion: ~12.6V full, ~9.0V cutoff)

Wiring (INA219 breakout board):
  VCC  → Pi 3.3V  (pin 1)
  GND  → Pi GND   (pin 6)
  SDA  → Pi SDA   (pin 3 / GPIO2)
  SCL  → Pi SCL   (pin 5 / GPIO3)
  V+   → Battery positive side of shunt resistor
  V-   → Load/charger positive terminal

Install dependencies:
  pip install adafruit-circuitpython-ina219 adafruit-blinka

Enable I2C on the Pi:
  sudo raspi-config → Interface Options → I2C → Enable
"""

import time
import json
import os
import signal
import sys
from collections import deque

# --- Try to import RPi.GPIO for relay control ---
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("[WARNING] RPi.GPIO not found. Relay control disabled (simulation mode).")

# --- Try to import the INA219 library ---
try:
    import board
    import busio
    from adafruit_ina219 import INA219, ADCResolution, Mode
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    print("[WARNING] Adafruit INA219 library not found. Running in SIMULATION mode.")
    print("          Install with: pip install adafruit-circuitpython-ina219 adafruit-blinka\n")

# =============================================================================
# CONFIGURATION — edit these to match your battery
# =============================================================================

BATTERY_CAPACITY_MAH  = 2600.0   # Rated capacity of your battery (mAh)
BATTERY_FULL_VOLTAGE  = 12.6     # Voltage at 100% SoC (4.2V × 3 cells)
BATTERY_EMPTY_VOLTAGE = 9.0      # Voltage at 0% SoC  (3.0V × 3 cells)

SHUNT_OHMS            = 0.1      # Shunt resistor on INA219 board (Ω)
MAX_EXPECTED_AMPS     = 6.0      # Max current from charger spec (6A)

SAMPLE_INTERVAL_S     = 1.0      # How often to sample (seconds)
SOC_FILE              = "soc_state.json"  # Persisted SoC between runs

# Coulomb counting efficiency factor (accounts for charging inefficiency)
COULOMBIC_EFFICIENCY  = 0.98

# Low SoC warning threshold
LOW_SOC_WARN_PCT      = 20.0

# Number of recent current samples to average for time estimates (smoothing)
CURRENT_SMOOTH_WINDOW = 30

# Relay GPIO pin (BCM numbering) — HIGH = relay ON, LOW = relay OFF
# Wiring: GPIO17 (pin 11) → relay IN, Pi 5V → relay VCC, Pi GND → relay GND
RELAY_PIN = 17

# =============================================================================
# INA219 SENSOR WRAPPER
# =============================================================================

class BatterySensor:
    """Wraps the INA219 for clean voltage / current readings."""

    def __init__(self):
        if HARDWARE_AVAILABLE:
            i2c = busio.I2C(board.SCL, board.SDA)
            self.sensor = INA219(i2c, reset=False)
            self.sensor.bus_voltage_range = 0  # 16V range
            self.sensor.gain = INA219.GAIN_8_320MV
            self.sensor.bus_adc_resolution = ADCResolution.ADCRES_12BIT_32S
            self.sensor.shunt_adc_resolution = ADCResolution.ADCRES_12BIT_32S
            self.sensor.mode = Mode.SANDBURST
            print("INA219 sensor initialised on I2C bus.")
        else:
            self._sim_soc = 75.0
            self._sim_t   = 0

    def read(self):
        """
        Returns (voltage_V, current_mA, power_mW).
        Current > 0 = discharging, current < 0 = charging.
        """
        if HARDWARE_AVAILABLE:
            voltage    = self.sensor.bus_voltage
            current_ma = self.sensor.current
            power_mw   = self.sensor.power
            return voltage, current_ma, power_mw
        else:
            self._sim_t += SAMPLE_INTERVAL_S
            current_ma = -1800.0 if self._sim_t % 60 < 30 else 300.0
            soc_frac   = max(0, min(1, self._sim_soc / 100.0))
            voltage    = BATTERY_EMPTY_VOLTAGE + soc_frac * (BATTERY_FULL_VOLTAGE - BATTERY_EMPTY_VOLTAGE)
            power_mw   = voltage * current_ma
            return voltage, current_ma, power_mw

# =============================================================================
# STATE OF CHARGE TRACKER
# =============================================================================

class SoCTracker:
    """
    Coulomb Counter for State of Charge estimation.

    SoC(t) = SoC(t-1) - (I × Δt) / (Capacity × 3600) × 100

    Sign convention:
      current_mA > 0 : discharging
      current_mA < 0 : charging
    """

    def __init__(self, sensor: BatterySensor):
        self.sensor          = sensor
        self.capacity_mah    = BATTERY_CAPACITY_MAH
        self.soc_pct         = self._load_or_estimate_soc()
        self.charge_mah      = self.soc_pct / 100.0 * self.capacity_mah
        self.last_time       = time.monotonic()
        self.running         = True
        self._current_window = deque(maxlen=CURRENT_SMOOTH_WINDOW)

        print(f"SoC tracker started. Initial SoC: {self.soc_pct:.1f}%  "
              f"({self.charge_mah:.0f} mAh remaining)\n")

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load_or_estimate_soc(self):
        """Load last known SoC from disk, or estimate from open-circuit voltage."""
        if os.path.exists(SOC_FILE):
            try:
                with open(SOC_FILE) as f:
                    data = json.load(f)
                soc   = float(data.get("soc_pct", 50.0))
                age_s = time.time() - float(data.get("saved_at", 0))
                print(f"Loaded persisted SoC: {soc:.1f}%  (saved {age_s/60:.1f} min ago)")
                return max(0.0, min(100.0, soc))
            except Exception as e:
                print(f"Could not read {SOC_FILE}: {e}")

        print("No saved SoC found — estimating from open-circuit voltage.")
        return self._ocv_to_soc()

    def _ocv_to_soc(self):
        """
        Piecewise linear OCV→SoC for a 3S Li-ion pack.
        Best accuracy when battery has rested with no load.

        3S OCV lookup:
          12.60V = 100%   12.42V = 90%   12.18V = 70%
          11.94V =  50%   11.58V = 30%   11.22V = 10%
           9.00V =   0%
        """
        ocv_soc_table = [
            (12.60, 100.0), (12.42, 90.0), (12.18, 70.0),
            (11.94,  50.0), (11.58, 30.0), (11.22, 10.0),
            ( 9.00,   0.0),
        ]
        voltage, _, _ = self.sensor.read()
        for i in range(len(ocv_soc_table) - 1):
            v_high, s_high = ocv_soc_table[i]
            v_low,  s_low  = ocv_soc_table[i + 1]
            if voltage >= v_low:
                ratio = (voltage - v_low) / (v_high - v_low)
                soc   = s_low + ratio * (s_high - s_low)
                print(f"OCV = {voltage:.3f}V → estimated SoC = {soc:.1f}%")
                return max(0.0, min(100.0, soc))
        return 0.0

    def save_state(self):
        """Persist current SoC to disk."""
        try:
            with open(SOC_FILE, "w") as f:
                json.dump({"soc_pct": self.soc_pct, "saved_at": time.time()}, f)
        except Exception as e:
            print(f"Could not save state: {e}")

    # ------------------------------------------------------------------
    # Core update loop
    # ------------------------------------------------------------------

    def update(self):
        """Read sensor, integrate coulombs, update SoC."""
        now     = time.monotonic()
        delta_s = now - self.last_time
        self.last_time = now

        voltage, current_ma, power_mw = self.sensor.read()
        self._current_window.append(current_ma)

        eff       = COULOMBIC_EFFICIENCY if current_ma < 0 else 1.0
        delta_mah = current_ma * (delta_s / 3600.0) * eff
        self.charge_mah -= delta_mah
        self.charge_mah  = max(0.0, min(self.capacity_mah, self.charge_mah))
        self.soc_pct     = (self.charge_mah / self.capacity_mah) * 100.0

        return voltage, current_ma, power_mw

    # ------------------------------------------------------------------
    # Time-to-full / time-to-empty estimates
    # ------------------------------------------------------------------

    def _smoothed_current(self):
        """Average current over the recent sample window (mA)."""
        if not self._current_window:
            return 0.0
        return sum(self._current_window) / len(self._current_window)

    def time_to_empty(self):
        """
        Estimated minutes until battery is empty at current discharge rate.
        Returns None if not discharging or current is negligible.
        """
        avg_ma = self._smoothed_current()
        if avg_ma <= 5.0:
            return None
        return (self.charge_mah / avg_ma) * 60.0  # minutes

    def time_to_full(self):
        """
        Estimated minutes until battery is full at current charge rate.
        Returns None if not charging or current is negligible.
        """
        avg_ma = self._smoothed_current()
        if avg_ma >= -5.0:
            return None
        charge_rate_ma = abs(avg_ma) * COULOMBIC_EFFICIENCY
        remaining_mah  = self.capacity_mah - self.charge_mah
        return (remaining_mah / charge_rate_ma) * 60.0  # minutes

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    @staticmethod
    def _fmt_minutes(minutes):
        """Format minutes as 'Xh Ym' or 'Ym'."""
        if minutes is None:
            return "--"
        m = int(minutes)
        if m >= 60:
            return f"{m // 60}h {m % 60:02d}m"
        return f"{m}m"

    def print_status(self, voltage, current_ma, power_mw):
        """Print a clean multi-line status block, refreshing in place."""
        W = 55  # box inner width

        bar_len = W - 2
        filled  = int(self.soc_pct / 100.0 * bar_len)
        bar     = "█" * filled + "░" * (bar_len - filled)

        is_charging = current_ma < -5.0
        is_idle     = abs(current_ma) <= 5.0
        state       = "CHARGING" if is_charging else ("IDLE" if is_idle else "DISCHARGING")

        tte = self.time_to_empty()
        ttf = self.time_to_full()

        # Estimated SoC ±2% uncertainty band
        soc_lo  = max(0.0,                self.soc_pct - 2.0)
        soc_hi  = min(100.0,              self.soc_pct + 2.0)
        cap_lo  = soc_lo / 100.0 * self.capacity_mah
        cap_hi  = soc_hi / 100.0 * self.capacity_mah
        full_lo = soc_lo / 100.0 * self.capacity_mah   # mAh if this were "full" reference
        full_hi = soc_hi / 100.0 * self.capacity_mah

        warn = "  ⚠ LOW BATTERY" if (self.soc_pct < LOW_SOC_WARN_PCT and not is_charging) else ""

        def row(content):
            # Pad content to fixed inner width and wrap in box chars
            return f"│ {content:<{W}} │"

        lines = [
            f"┌{'─' * (W + 2)}┐",
            row(f"12V Li-ion Pack  │  {state}  │  {voltage:.3f} V"),
            f"├{'─' * (W + 2)}┤",
            row(f"[{bar}]"),
            row(""),
            row(f"  SoC         :  {self.soc_pct:5.1f}%   (est. {soc_lo:.1f}% – {soc_hi:.1f}%){warn}"),
            row(f"  Capacity    :  {self.charge_mah:6.0f} mAh  (est. {cap_lo:.0f} – {cap_hi:.0f} mAh)"),
            row(f"  Est. @ full :  {self.capacity_mah:.0f} mAh  (range {cap_lo / self.soc_pct * 100:.0f} – {cap_hi / self.soc_pct * 100:.0f} mAh)" if self.soc_pct > 1 else row("  Est. @ full :  --")),
            row(""),
            row(f"  Current     :  {current_ma:+8.1f} mA"),
            row(f"  Power       :  {power_mw:8.1f} mW"),
            row(""),
            row(f"  Time to empty : {self._fmt_minutes(tte):<12}  Time to full : {self._fmt_minutes(ttf)}"),
            f"└{'─' * (W + 2)}┘",
        ]

        if hasattr(self, '_printed_lines'):
            print(f"\033[{self._printed_lines}A", end="")
        self._printed_lines = len(lines)

        print("\n".join(lines), flush=True)

# =============================================================================
# MAIN
# =============================================================================

def relay_on():
    """Energise the relay on GPIO17."""
    if GPIO_AVAILABLE:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(RELAY_PIN, GPIO.OUT)
        GPIO.output(RELAY_PIN, GPIO.HIGH)
        print(f"Relay ON  (GPIO{RELAY_PIN})")
    else:
        print(f"[SIM] Relay ON  (GPIO{RELAY_PIN})")


def relay_off():
    """De-energise the relay and clean up the GPIO pin."""
    if GPIO_AVAILABLE:
        GPIO.output(RELAY_PIN, GPIO.LOW)
        GPIO.cleanup(RELAY_PIN)
        print(f"Relay OFF (GPIO{RELAY_PIN})")
    else:
        print(f"[SIM] Relay OFF (GPIO{RELAY_PIN})")


def main():
    relay_on()

    sensor  = BatterySensor()
    tracker = SoCTracker(sensor)

    def shutdown(sig, frame):
        print("\n\nShutting down — saving state...")
        tracker.save_state()
        relay_off()
        print(f"Final SoC: {tracker.soc_pct:.1f}%")
        sys.exit(0)

    signal.signal(signal.SIGINT,  shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print("╔═══════════════════════════════════════════════════════╗")
    print("║   12V Li-ion SoC Monitor  (Coulomb Counting)         ║")
    print("║   Battery: 2600mAh  |  Sensor: INA219                ║")
    print("║   Press Ctrl+C to exit and save state                ║")
    print("╚═══════════════════════════════════════════════════════╝\n")

    iteration = 0
    while tracker.running:
        voltage, current_ma, power_mw = tracker.update()
        tracker.print_status(voltage, current_ma, power_mw)

        # Save state every 60 samples (~1 min at default interval)
        if iteration % 60 == 0:
            tracker.save_state()

        if tracker.soc_pct <= 0.5:
            print("\n[ALERT] Battery is empty! Stopping to protect battery.")
            tracker.save_state()
            relay_off()
            break
        if tracker.soc_pct >= 99.9 and current_ma < 0:
            print("\n[INFO] Battery fully charged!")

        iteration += 1
        time.sleep(SAMPLE_INTERVAL_S)

    tracker.save_state()
    relay_off()


if __name__ == "__main__":
    main()