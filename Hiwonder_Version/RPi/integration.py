from soc import relay_on, relay_off


try:
    relay_on()
finally:
    relay_off()