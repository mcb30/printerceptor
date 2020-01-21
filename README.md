Print job interceptor
=====================

This daemon allows for the transparent interception of network printer
jobs.  The expected setup is that a Linux box (the `printerceptor`)
with two or more Ethernet ports is inserted between the network
printer(s) and the switch to which the printers were previously
connected:

```
Original setup:

  +--------+                           +---------+
  |        |---------------------------| printer |
  |        |                           +---------+
  | switch |
  |        |                           +---------+
  |        |---------------------------| printer |
  +--------+                           +---------+


New setup:

  +--------+     +---------------+     +---------+
  |        |     |               |-----| printer |
  |        |     |               |     +---------+
  | switch |-----| printerceptor |
  |        |     |               |     +---------+
  |        |     |               |-----| printer |
  +--------+     +---------------+     +---------+
```

The Ethernet ports are configured as members of a bridge, so that the
printer remains accessible using its original IP address.

The `printerceptor` machine is then configured to divert all
applicable traffic through itself.  For example, to intercept `lpd`
traffic on port `515`:

```
# Prevent port 515 traffic from being bridged in the usual way
#
ebtables -t broute -A BROUTING -p IPv4 --ip-proto tcp --ip-dport 515 \
	 -j redirect --redirect-target=DROP
ebtables -t broute -A BROUTING -p IPv4 --ip-proto tcp --ip-sport 515 \
	 -j redirect --redirect-target=DROP

# Mark any port 515 traffic with mark `1`
#
iptables -t mangle -A PREROUTING -p tcp --dport 515 -j MARK --set-mark 1

# Treat any traffic with mark `1` as local
#
ip rule add fwmark 1 lookup 100
ip route add local 0.0.0.0/0 dev lo table 100
```

The `printerceptor` machine can then run the `printerceptor` daemon:

```
printerceptor lpd -o /var/spool/printouts
```

Any intercepted printouts will then be saved to `/var/spool/printouts`.
