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

        self.data = pd.DataFrame(
            columns=[
                'idx', 'ifDescr',
                'ifName', 'ifSpeed',
                'ifAdminStatus', 'ifOperStatus',
                'ifHCInOctets', 'ifHCOutOctets',
                'jnxDomCurrentRxLaserPower', 'jnxDomCurrentRxLaserPowerLowWarningThreshold'
            ]
        )

        if os.path.exists(f"./output/{hostname}.temp.csv"):
            self.prev_data = pd.read_csv(f'./output/{hostname}.temp.csv')
            self.prev_data.set_index('idx', inplace=True)
        else:
            self.prev_data = pd.DataFrame()

        if os.path.exists(f"./output/{hostname}.temp.json"):
            with open(f"./output/{hostname}.temp.json", 'r') as f:
                data = json.load(f)
            self.prev_t_in = data["prev_t_in"]
            self.prev_t_out = data["prev_t_out"]
        else:
            self.prev_t_in = time.time()
            self.prev_t_out = time.time()

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
            self.data['idx'] = self.data['idx'].astype('object')
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

    async def walk_ifHCInOctets(self):
        time.sleep(0.5)
        try:
            print(f"[.] {self.hostname}: Getting interfaces' HCInOctets")
            # async for req_oid, val in self.client.walk(".1.3.6.1.2.1.2.2.1.10"):
            async for req_oid, val in self.client.walk(".1.3.6.1.2.1.31.1.1.1.6"):
                self.data.loc[req_oid.split('.')[-1], 'ifHCInOctets'] = val
                self.t_in = time.time()
        except Exception as e:
            print(f"[-] {self.hostname}: Error during SNMP walk HCInOctets: {e}")

    async def walk_ifHCOutOctets(self):
        time.sleep(0.5)
        try:
            print(f"[.] {self.hostname}: Getting interfaces' HCOutOctets")
            # async for req_oid, val in self.client.walk(".1.3.6.1.2.1.2.2.1.16"):
            async for req_oid, val in self.client.walk(".1.3.6.1.2.1.31.1.1.1.10"):
                self.data.loc[req_oid.split('.')[-1], 'ifHCOutOctets'] = val
                self.t_out = time.time()
        except Exception as e:
            print(f"[-] {self.hostname}: Error during SNMP walk HCOutOctets: {e}")

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

    @staticmethod
    def traffic_calc(ifHCInOctets_1, t1, ifHCInOctets_2, t2):
        if ifHCInOctets_2 >= ifHCInOctets_1:
            result = ((ifHCInOctets_2 - ifHCInOctets_1)*8)/(t2 - t1)
        else:
            # return ((4_294_967_295 - ifHCInOctets_1) + ifHCInOctets_2 + 1)/(t2 - t1)
            result = (((18_446_744_073_709_551_615 - ifHCInOctets_1) + ifHCInOctets_2 + 1)*8)/(t2 - t1)
        return round(result)

    def cleanData(self):
        self.data = self.data[self.data['ifName'] != b'']
        self.data['ifName'] = self.data['ifName'].str.decode('utf-8', errors='replace')
        self.data['ifDescr'] = self.data['ifDescr'].str.decode('utf-8', errors='replace')
        self.data['ifDescr'] = self.data['ifDescr'].str.replace('/', '_')
        self.data['ifDescr'] = self.data['ifDescr'].str.replace('.', '+')

        self.data['ifSpeed'] = self.data['ifSpeed'].astype(int)
        self.data['jnxDomCurrentRxLaserPower'] = self.data['jnxDomCurrentRxLaserPower']*0.01
        self.data['jnxDomCurrentRxLaserPower'] = self.data['jnxDomCurrentRxLaserPower'].round(2)
        self.data['jnxDomCurrentRxLaserPowerLowWarningThreshold'] = self.data['jnxDomCurrentRxLaserPowerLowWarningThreshold']*0.01
        self.data['jnxDomCurrentRxLaserPowerLowWarningThreshold'] = self.data['jnxDomCurrentRxLaserPowerLowWarningThreshold'].round(2)

        status_map = {1: "up", 2: "down"}
        self.data['ifAdminStatus'] = self.data['ifAdminStatus'].map(status_map).fillna("testing")
        self.data['ifOperStatus'] = self.data['ifOperStatus'].map(status_map).fillna("testing")

    @staticmethod
    def saveFileInJson(file_name, data):
        with open(file_name, 'w') as f:
            json.dump(data, f)

    def saveData(self):
        now_local = datetime.now(timezone(timedelta(hours=7)))
        nanoseconds = time.time_ns() % 1_000_000_000
        timestamp = f"{now_local.strftime('%Y-%m-%dT%H:%M:%S')}.{nanoseconds:09d}Z"

        data_name = {'lastUpdate': timestamp}
        data_speed = {'lastUpdate': timestamp}
        data_adminStatus = {'lastUpdate': timestamp}
        data_operStatus = {'lastUpdate': timestamp}
        data_inboundTraffic = {'lastUpdate': timestamp}
        data_outboundTraffic = {'lastUpdate': timestamp}
        data_currentRxLaserPower = {'lastUpdate': timestamp}
        data_currentRxLaserPowerLowWarningThreshold = {'lastUpdate': timestamp}

        for row in self.data.itertuples():
            data_name[f'interface.{row[1]}.name'] = row[2]
            data_speed[f'interface.{row[1]}.speed'] = row[3]
            data_adminStatus[f'interface.{row[1]}.adminStatus'] = row[4]
            data_operStatus[f'interface.{row[1]}.operStatus'] = row[5]

            try:
                data_inboundTraffic[f'interface.{row[1]}.inboundTraffic'] = self.traffic_calc(self.prev_data.at[int(row[0]), 'ifHCInOctets'], self.prev_t_in, row[6], self.t_in)
            except:
                data_inboundTraffic[f'interface.{row[1]}.inboundTraffic'] = 0

            try:
                data_outboundTraffic[f'interface.{row[1]}.outboundTraffic'] = self.traffic_calc(self.prev_data.at[int(row[0]), 'ifHCOutOctets'], self.prev_t_out, row[7], self.t_out)
            except:
                data_outboundTraffic[f'interface.{row[1]}.outboundTraffic'] = 0

            if pd.notna(row[8]):
                data_currentRxLaserPower[f'interface.{row[1]}.currentRxLaserPower'] = row[8]
            if pd.notna(row[9]):
                data_currentRxLaserPowerLowWarningThreshold[f'interface.{row[1]}.currentRxLaserPowerLowWarningThreshold'] = row[9]

        self.data[['ifHCInOctets', 'ifHCOutOctets']].to_csv(f'./output/{self.hostname}.temp.csv')
        self.saveFileInJson(f"./output/{self.hostname}.temp.json", {"prev_t_in": self.t_in, "prev_t_out": self.t_out})
        self.saveFileInJson(f"./output/{self.hostname}.name.json", data_name)
        self.saveFileInJson(f"./output/{self.hostname}.speed.json", data_speed)
        self.saveFileInJson(f"./output/{self.hostname}.adminStatus.json", data_adminStatus)
        self.saveFileInJson(f"./output/{self.hostname}.operStatus.json", data_operStatus)
        self.saveFileInJson(f"./output/{self.hostname}.inboundTraffic.json", data_inboundTraffic)
        self.saveFileInJson(f"./output/{self.hostname}.outboundTraffic.json", data_outboundTraffic)
        self.saveFileInJson(f"./output/{self.hostname}.currentRxLaserPower.json", data_currentRxLaserPower)
        self.saveFileInJson(f"./output/{self.hostname}.currentRxLaserPowerLowWarningThreshold.json", data_currentRxLaserPowerLowWarningThreshold)

    async def gather_data(self):
        check = await self.check_connection()
        if check:
            await self.walk_ifAlias()
            await self.walk_ifDescr()
            await self.walk_ifSpeed()
            await self.walk_ifAdminStatus()
            await self.walk_ifOperStatus()
            await self.walk_ifHCInOctets()
            await self.walk_ifHCOutOctets()
            await self.walk_jnxDomCurrentRxLaserPower()
            await self.walk_jnxDomCurrentRxLaserPowerLowWarningThreshold()
            print(f"[+] {self.hostname}: Gathering SNMP info successfully")

    def run(self):
        os.makedirs("./output", exist_ok=True)
        asyncio.run(self.gather_data())
        self.cleanData()
        self.saveData()


if __name__ == "__main__":
    pass
