import network


sta = network.WLAN(network.STA_IF)
sta.active(True)
mac = sta.config("mac")
print(":".join("%02X" % byte for byte in mac))

