#!/usr/bin/env python3

import asyncio
import json
import os
import pandas as pd
import time
import warnings

from datetime import datetime, timedelta, timezone
from puresnmp import Client, V2C, PyWrapper


warnings.filterwarnings('ignore')


class SNMPHandler:
    def __init__(self, host, port, community, hostname):
        self.hostname = hostname
        self.client = PyWrapper(Client(host, V2C(community), port=port))

        columns = [
            'idx', 'ifDescr',
            'ifName', 'ifSpeed',
            'ifAdminStatus', 'ifOperStatus',
            'ifInOctets', 'ifOutOctets',
            'jnxDomCurrentRxLaserPower', 'jnxDomCurrentRxLaserPowerLowWarningThreshold'
        ]
        self.data = pd.DataFrame(columns=columns)
        self.data = self.data.astype({'ifName': 'object', 'ifDescr': 'object'})

    async def check_connection(self):
        try:
            print(f"[.] {self.hostname}: Checking connection")
            await self.client.get('.1.3.6.1.2.1.1.3.0')
            return True
        except Exception:
            print(f"[-] {self.hostname}: Failed to connect to the device")
            return False

    async def walk_ifAlias(self):
        time.sleep(0.5)
        try:
            print(f"[.] {self.hostname}: Getting interfaces' Alias")
            async for req_oid, val in self.client.walk(".1.3.6.1.2.1.31.1.1.1.18"):
                self.data.loc[len(self.data)] = {
                    'idx': req_oid.split('.')[-1],
                    'ifName': val
                }
            self.data.set_index('idx', inplace=True)
        except Exception as e:
            print(f"[-] {self.hostname}: Error during SNMP walk Alias: {e}")

    async def walk_ifDescr(self):
        time.sleep(0.5)
        try:
            print(f"[.] {self.hostname}: Getting interfaces' Description")
            async for req_oid, val in self.client.walk(".1.3.6.1.2.1.2.2.1.2"):
                self.data.loc[req_oid.split('.')[-1], 'ifDescr'] = val
        except Exception as e:
            print(f"[-] {self.hostname}: Error during SNMP walk Description: {e}")

    async def walk_ifSpeed(self):
        time.sleep(0.5)
        try:
            print(f"[.] {self.hostname}: Getting interfaces' Speed")
            async for req_oid, val in self.client.walk(".1.3.6.1.2.1.2.2.1.5"):
                self.data.loc[req_oid.split('.')[-1], 'ifSpeed'] = val
        except Exception as e:
            print(f"[-] {self.hostname}: Error during SNMP walk Speed: {e}")

    async def walk_ifAdminStatus(self):
        time.sleep(0.5)
        try:
            print(f"[.] {self.hostname}: Getting interfaces' AdminStatus")
            async for req_oid, val in self.client.walk(".1.3.6.1.2.1.2.2.1.7"):
                self.data.loc[req_oid.split('.')[-1], 'ifAdminStatus'] = val
        except Exception as e:
            print(f"[-] {self.hostname}: Error during SNMP walk AdminStatus: {e}")

    async def walk_ifOperStatus(self):
        time.sleep(0.5)
        try:
            print(f"[.] {self.hostname}: Getting interfaces' OperStatus")
            async for req_oid, val in self.client.walk(".1.3.6.1.2.1.2.2.1.8"):
                self.data.loc[req_oid.split('.')[-1], 'ifOperStatus'] = val
        except Exception as e:
            print(f"[-] {self.hostname}: Error during SNMP walk OperStatus: {e}")

    async def walk_ifInOctets(self):
        time.sleep(0.5)
        try:
            print(f"[.] {self.hostname}: Getting interfaces' InOctets")
            async for req_oid, val in self.client.walk(".1.3.6.1.2.1.2.2.1.10"):
                self.data.loc[req_oid.split('.')[-1], 'ifInOctets'] = val
        except Exception as e:
            print(f"[-] {self.hostname}: Error during SNMP walk InOctets: {e}")

    async def walk_ifOutOctets(self):
        time.sleep(0.5)
        try:
            print(f"[.] {self.hostname}: Getting interfaces' OutOctets")
            async for req_oid, val in self.client.walk(".1.3.6.1.2.1.2.2.1.16"):
                self.data.loc[req_oid.split('.')[-1], 'ifOutOctets'] = val
        except Exception as e:
            print(f"[-] {self.hostname}: Error during SNMP walk OutOctets: {e}")

    async def walk_jnxDomCurrentRxLaserPower(self):
        time.sleep(0.5)
        try:
            print(f"[.] {self.hostname}: Getting interfaces' CurrentRxLaserPower")
            async for req_oid, val in self.client.walk(".1.3.6.1.4.1.2636.3.60.1.1.1.1.5"):
                self.data.loc[req_oid.split('.')[-1], 'jnxDomCurrentRxLaserPower'] = val
        except Exception as e:
            print(f"[-] {self.hostname}: Error during SNMP walk CurrentRxLaserPower: {e}")

    async def walk_jnxDomCurrentRxLaserPowerLowWarningThreshold(self):
        time.sleep(0.5)
        try:
            print(f"[.] {self.hostname}: Getting interfaces' CurrentRxLaserPowerLowWarningThreshold")
            async for req_oid, val in self.client.walk(".1.3.6.1.4.1.2636.3.60.1.1.1.1.12"):
                self.data.loc[req_oid.split('.')[-1], 'jnxDomCurrentRxLaserPowerLowWarningThreshold'] = val
        except Exception as e:
            print(f"[-] {self.hostname}: Error during SNMP walk CurrentRxLaserPowerLowWarningThreshold: {e}")

    def cleanData(self):
        self.data = self.data[self.data['ifName'] != b'']
        self.data['ifName'] = self.data['ifName'].str.decode('utf-8', errors='replace')
        self.data['ifDescr'] = self.data['ifDescr'].str.decode('utf-8', errors='replace')
        self.data['ifDescr'] = self.data['ifDescr'].str.replace('/', '_')
        self.data['ifDescr'] = self.data['ifDescr'].str.replace('.', '+')

    def saveData(self):
        now_local = datetime.now(timezone(timedelta(hours=7)))
        nanoseconds = time.time_ns() % 1_000_000_000
        timestamp = f"{now_local.strftime('%Y-%m-%dT%H:%M:%S')}.{nanoseconds:09d}Z"

        data_ifAlias = {'lastUpdate': timestamp}
        data_ifSpeed = {'lastUpdate': timestamp}
        data_ifAdminStatus = {'lastUpdate': timestamp}
        data_ifOperStatus = {'lastUpdate': timestamp}
        data_ifInOctets = {'lastUpdate': timestamp}
        data_ifOutOctets = {'lastUpdate': timestamp}
        data_jnxDomCurrentRxLaserPower = {'lastUpdate': timestamp}
        data_jnxDomCurrentRxLaserPowerLowWarningThreshold = {'lastUpdate': timestamp}

        for row in self.data.itertuples():
            data_ifAlias[f'interface.{row[1]}.name'] = row[2]
            data_ifSpeed[f'interface.{row[1]}.speed'] = row[3]
            data_ifAdminStatus[f'interface.{row[1]}.adminStatus'] = row[4]
            data_ifOperStatus[f'interface.{row[1]}.operStatus'] = row[5]
            data_ifInOctets[f'interface.{row[1]}.inOctets'] = row[6]
            data_ifOutOctets[f'interface.{row[1]}.outOctets'] = row[7]
            if pd.notna(row[8]):
                data_jnxDomCurrentRxLaserPower[f'interface.{row[1]}.currentRxLaserPower'] = row[8]
            if pd.notna(row[9]):
                data_jnxDomCurrentRxLaserPowerLowWarningThreshold[f'interface.{row[1]}.currentRxLaserPowerLowWarningThreshold'] = row[9]

        # self.data.to_csv('result.csv')
        os.makedirs("./output", exist_ok=True)
        with open(f"./output/{self.hostname}.ifAlias.json", 'w') as f:
            json.dump(data_ifAlias, f)
        with open(f"./output/{self.hostname}.ifSpeed.json", 'w') as f:
            json.dump(data_ifSpeed, f)
        with open(f"./output/{self.hostname}.ifAdminStatus.json", 'w') as f:
            json.dump(data_ifAdminStatus, f)
        with open(f"./output/{self.hostname}.ifOperStatus.json", 'w') as f:
            json.dump(data_ifOperStatus, f)
        with open(f"./output/{self.hostname}.ifInOctets.json", 'w') as f:
            json.dump(data_ifInOctets, f)
        with open(f"./output/{self.hostname}.ifOutOctets.json", 'w') as f:
            json.dump(data_ifOutOctets, f)
        with open(f"./output/{self.hostname}.jnxDomCurrentRxLaserPower.json", 'w') as f:
            json.dump(data_jnxDomCurrentRxLaserPower, f)
        with open(f"./output/{self.hostname}.jnxDomCurrentRxLaserPowerLowWarningThreshold.json", 'w') as f:
            json.dump(data_jnxDomCurrentRxLaserPowerLowWarningThreshold, f)

    async def gather_data(self):
        check = await self.check_connection()
        if check:
            await self.walk_ifAlias()
            await self.walk_ifDescr()
            await self.walk_ifSpeed()
            await self.walk_ifAdminStatus()
            await self.walk_ifOperStatus()
            await self.walk_ifInOctets()
            await self.walk_ifOutOctets()
            await self.walk_jnxDomCurrentRxLaserPower()
            await self.walk_jnxDomCurrentRxLaserPowerLowWarningThreshold()
            print(f"[+] {self.hostname}: Gathering SNMP info successfully")

    def run(self):
        asyncio.run(self.gather_data())
        self.cleanData()
        self.saveData()


if __name__ == "__main__":
    pass
