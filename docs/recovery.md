# Recovering the spa's Wi-Fi locally

A brief unavailable state can mean a radio/link dropout, an IP address change, or
AP fallback. It does not by itself prove that stored Wi-Fi credentials were lost.
First check the router's client list and whether the spa rejoins home Wi-Fi.
A DHCP reservation stabilizes its home IP address; it cannot repair the radio or
prevent AP fallback. Use a simple compatible 2.4 GHz WPA2 network and check signal
strength at the spa. Home Assistant on Ethernet cannot reach the spa's isolated AP
unless another interface/device is manually connected to that AP.

The user has verified the provisioning ACK in the existing manual workflow. This
new helper has unit tests but has **not yet been run against spa hardware**. An ACK
only confirms receipt of the provisioning command, not successful authentication,
DHCP, or continued Wi-Fi connectivity. No cloud account is needed.

## iPhone and a-Shell

1. Copy `tools/recover_wifi.py` onto the iPhone using Files. Keep the filename
   exactly `recover_wifi.py` (not `.py.txt`). Put it in the a-Shell folder visible
   under **On My iPhone**, or use a-Shell's `pickFolder` to select the folder where
   you saved it. In a-Shell, run `ls` and confirm that same filename is listed in
   the current folder before running it.
2. In iOS Settings → Wi-Fi, manually join the spa's `BW-Airjet-V01-xxxx` AP using
   password `123456789`. Accept staying connected without Internet. Check that
   this is your intended spa. The helper never connects to an AP itself.
3. Allow a-Shell **Local Network** access when prompted (or enable it in iOS
   Settings → Privacy & Security → Local Network). Return to a-Shell without
   switching away from the spa AP.
4. Run `python3 recover_wifi.py`. Python 3.11 or newer is supported; no packages,
   Home Assistant installation, or app imports are needed. Enter the **home**
   2.4 GHz SSID and password at the prompts. Password input is hidden. These are
   distinct from the spa AP password. Do not put credentials on the command line.
5. If a valid ACK appears, reconnect the iPhone to home Wi-Fi, check the router
   for the spa's DHCP lease, and then check Home Assistant. If it does not join,
   verify the entered network details and Wi-Fi compatibility before retrying.

`python3 recover_wifi.py --help` shows options. The default destination is
`10.10.100.254`, UDP port `12414`; `--host` accepts an alternative IPv4 gateway
only when you know it is the intended spa AP. `--timeout 2` sets each response
wait (greater than zero, at most ten seconds). There are at most three sends.
Foreign or malformed replies do not count as an ACK. No credentials or packet
dumps are printed or saved. The terminal must support hidden input; the helper
refuses an echoing password fallback.

SSID validation uses 1–32 UTF-8 **bytes**. Passwords may be empty for an open
network, 8–63 printable ASCII characters, or a 64-digit hexadecimal PSK. Invalid
input is rejected before network access. Credentials necessarily travel to the
AP in the spa's local provisioning protocol; join only your intended spa AP.

The helper never resets the spa, sends credentials automatically in the
background, or repairs radio coverage. If it times out, recheck the iPhone's AP
connection, local network permission, and gateway. A spa may leave the AP before
an ACK reaches the phone; inspect the home router before sending again. Repeated
fallback warrants checking signal, interference, power, and firmware/hardware
separately from credential recovery.

## Why the helper is standalone

The small command-1 framing routine is intentionally duplicated so a-Shell can
run this single file without the Home Assistant integration. It uses the V01
magic preamble, MQTT remaining length, zero flags, command 1, and two-byte
big-endian UTF-8 credential lengths. It accepts only the exact empty command-2
ACK from the selected gateway and UDP port. It does not discover identity or
assume that an empty device ID means invalid hardware.
