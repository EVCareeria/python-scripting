#!/usr/bin/env python

import scapy.all as scapy
import optparse

def scan(ip):
    arp_request = scapy.ARP(pdst=ip)
    broadcast = scapy.Ether(dst="ff:ff:ff:ff:ff:ff")
    arp_request_broadcast = broadcast/arp_request
    answered_list = scapy.srp(arp_request_broadcast, timeout=1, verbose=False)[0]

    clients_list = []

    for element in answered_list:
        client_dict = {"ip": element[0].psrc, "MAC":element[1].hwsrc}
        clients_list.append(client_dict)
        print(element[1].psrc + "\t\t" + element[1].hwsrc)
    return clients_list

def print_result(results_list):
    print("IP\t\t\tMAC ADDRESS\n--------------------------------------------------")
    for client in results_list:
        print(client)

if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option("-t", dest="target")
    (options, args) = parser.parse_args()
    result = scan(options.target)
    print_result(result)