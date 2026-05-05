from soc import relay_on, relay_off


try:
    while True:
        relay_on()
finally:
    relay_off()