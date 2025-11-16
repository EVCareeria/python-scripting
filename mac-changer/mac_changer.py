#!/usr/bin/env python

import subprocess
import optparse
import re

def get_arguments():
    parser = optparse.OptionParser()
    parser.add_option("-i", "--interface", dest="interface", help="Interface to change MAC address")
    parser.add_option("-m", "--mac", dest="new_mac", help="New MAC address")
    (options, args) = parser.parse_args()
    if not options.interface:
        parser.error("Interface must be specified")
    if not options.new_mac:
        parser.error("New MAC address must be specified")
    return options


def change_mac(interface, new_mac):
    print(f'Changing MAC address of {interface} to {new_mac}')
    subprocess.call(["ifconfig", interface, "down"])
    subprocess.call(["ifconfig", interface, "hw", "ether", new_mac])
    subprocess.call(["ifconfig", interface, "up"])

def get_current_mac(interface):
    check = subprocess.check_output(["ip", "a", "show", interface])
    regex = r'(?<=link/ether) (\w\w:\w\w:\w\w:\w\w:\w\w:\w\w)'
    result = re.search(regex, str(check))
    if result:
        print(result.group(0))
    else:
        print("No such interface")
    return result.group(0).strip()

from distlib.compat import raw_input

options = get_arguments()
get_current_mac(options.interface)
change_mac(options.interface, options.new_mac)
current_mac = get_current_mac(options.interface)
if current_mac != options.new_mac:
    print(f'Mac address was not changed from {current_mac} to {options.new_mac}')
else:
    print(f'Mac address was changed to {options.new_mac}')
