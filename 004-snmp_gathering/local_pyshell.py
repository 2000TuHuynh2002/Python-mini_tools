#!/usr/bin/env python3

import argparse
import textwrap

from local_snmp import SNMPHandler


def shell_handle():
    parser = argparse.ArgumentParser(
        prog='PROG',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent('''\
            Made by Tu Huynh 
            
            ███████ ███    ██ ███    ███ ██████      
            ██      ████   ██ ████  ████ ██   ██     
            ███████ ██ ██  ██ ██ ████ ██ ██████      
                 ██ ██  ██ ██ ██  ██  ██ ██          
            ███████ ██   ████ ██      ██ ██          
            
            -----------------------------------------
            '''
                                    ))

    parser.add_argument("host", type=str, help="the hostname or the ip of the host.")
    parser.add_argument('port', type=int, help="the device's SNMP port")
    parser.add_argument('community', type=str, help="the community for SNMP")
    parser.add_argument("name", type=str, help='the name of the device')

    args = parser.parse_args()

    if args.host == "" or args.port == "" or args.community == "" or args.name == "":
        print("The [host] [port] [commnity] [name] cannot be empty")
        return

    snmp = SNMPHandler(args.host, args.port, args.community, args.name)
    snmp.run()
    return


if __name__ == "__main__":
    shell_handle()
