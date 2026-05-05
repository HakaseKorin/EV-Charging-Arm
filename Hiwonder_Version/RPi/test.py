from soc import relay_on, relay_off, BatterySensor, SoCTracker

battery_sensor = BatterySensor()
soc_tracker = SoCTracker(battery_sensor)

try:
    while True:
        relay_on()
        voltage, current_ma, power_mw = soc_tracker.update()
        is_charging = current_ma < -5.0
        is_idle     = abs(current_ma) <= 5.0
        state       = "CHARGING" if is_charging else ("IDLE" if is_idle else "DISCHARGING")

        ttf = soc_tracker.time_to_full()
        ttf_formatted = soc_tracker.fmt_minutes(ttf)
        print(f"SoC: {soc_tracker.soc_pct:5.1f}%, ETA: {ttf_formatted}")
finally:
    relay_off()
    