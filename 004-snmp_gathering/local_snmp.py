#!/usr/bin/env python3

import asyncio
import json
import os
import pandas as pd
import time
import warnings

from datetime import datetime
from dotenv import load_dotenv
from elasticsearch import Elasticsearch, helpers
from puresnmp import Client, V2C, PyWrapper


load_dotenv()
warnings.filterwarnings('ignore')

ES_HOST = os.getenv('ES_HOST')
CA_CERT_PARTH = "./certs/ca.crt"
ES_USERNAME = os.getenv('TRANSPORT_USERNAME')
ES_PASSWORD = os.getenv('TRANSPORT_PASSWORD')


class SNMPHandler:
    def __init__(self, host, port, community, hostname):
        self.dt_now = datetime.now().replace(microsecond=0)
        self.dt_formatted = self.dt_now.strftime("%Y.%m.%d")
        self.hostname = hostname
        self.index_name = f"device-{hostname.lower().replace('-', '.')}-{self.dt_formatted}"
        self.client = PyWrapper(Client(host, V2C(community), port=port))
        self.esClient = Elasticsearch(
            [{'host': ES_HOST, 'port': 9200, 'scheme': 'https'}],
            basic_auth=(ES_USERNAME, ES_PASSWORD),
            ca_certs=CA_CERT_PARTH,
            verify_certs=False
        )
        self.data = pd.DataFrame(
            columns=[
                'idx', 'ifName',
                'ifDescr', 'ifSpeed',
                'ifAdminStatus', 'ifOperStatus',
                'ifHCInOctets', 'ifHCOutOctets',
                'jnxDomCurrentRxLaserPower',
                'jnxDomCurrentRxLaserPowerHighWarningThreshold',
                'jnxDomCurrentRxLaserPowerLowWarningThreshold'
            ]
        )

    def loadPrevData(self):
        if os.path.exists(f"./output/temp.{self.hostname}.csv"):
            self.prev_data = pd.read_csv(f'./output/temp.{self.hostname}.csv')
            self.prev_data.set_index('idx', inplace=True)
        else:
            self.prev_data = pd.DataFrame()
        if os.path.exists(f"./output/temp.{self.hostname}.json"):
            with open(f"./output/temp.{self.hostname}.json", 'r') as f:
                data = json.load(f)
            self.prev_t_in = data["prev_t_in"]
            self.prev_t_out = data["prev_t_out"]
        else:
            self.prev_t_in = time.time()
            self.prev_t_out = time.time()

    async def check_connection(self):
        try:
            print(f"[.][{self.dt_now}][{self.hostname}]: Checking connection")
            val = await self.client.get('.1.3.6.1.2.1.1.3.0')
            self.sys_uptime = int(val.total_seconds())
            return True
        except Exception:
            print(f"[-][{self.dt_now}][{self.hostname}]: Failed to connect to the device")
            return False

    async def get_sysInfo(self):
        time.sleep(1)
        try:
            print(f"[.][{self.dt_now}][{self.hostname}]: Getting SysInfo")
            val_sys_descr = await self.client.get('.1.3.6.1.2.1.1.1.0')
            val_sys_name = await self.client.get('.1.3.6.1.2.1.1.5.0')
            self.sys_descr = val_sys_descr.decode('utf-8', errors='replace')
            self.sys_name = val_sys_name.decode('utf-8', errors='replace')
            self.sys_temp = await self.client.get('.1.3.6.1.4.1.2636.3.1.13.1.7.9.1.0.0')
            self.sys_cpu = await self.client.get('.1.3.6.1.4.1.2636.3.1.13.1.8.9.1.0.0')
            self.sys_ram = await self.client.get('.1.3.6.1.4.1.2636.3.1.13.1.11.9.1.0.0')
        except Exception as e:
            print(f"[-][{self.dt_now}][{self.hostname}]: Error during SNMP get SysInfo: {e}")

    async def get_alarm(self):
        time.sleep(1)
        try:
            print(f"[.][{self.dt_now}][{self.hostname}]: Getting Alarm")
            alarm_map = {"1": "other", "2": "off", "3": "on"}
            val_yellow_state = await self.client.get('.1.3.6.1.4.1.2636.3.4.2.2.1.0')
            val_red_state = await self.client.get('.1.3.6.1.4.1.2636.3.4.2.3.1.0')
            self.yellow_state = alarm_map[str(val_yellow_state)]
            self.red_state = alarm_map[str(val_red_state)]
            self.yellow_count = await self.client.get('.1.3.6.1.4.1.2636.3.4.2.2.2.0')
            self.red_count = await self.client.get('.1.3.6.1.4.1.2636.3.4.2.3.2.0')
            val_yellow_lastChange = await self.client.get('.1.3.6.1.4.1.2636.3.4.2.2.3.0')
            val_red_lastChange = await self.client.get('.1.3.6.1.4.1.2636.3.4.2.3.3.0')
            self.yellow_lastChange = int(val_yellow_lastChange.total_seconds())
            self.red_lastChange = int(val_red_lastChange.total_seconds())
        except Exception as e:
            print(f"[-][{self.dt_now}][{self.hostname}]: Error during SNMP get Alarm: {e}")

    async def walk_ifAlias(self):
        time.sleep(1)
        try:
            print(f"[.][{self.dt_now}][{self.hostname}]: Getting interfaces' Alias")
            async for req_oid, val in self.client.walk(".1.3.6.1.2.1.31.1.1.1.18"):
                self.data.loc[len(self.data)] = {
                    'idx': req_oid.split('.')[-1],
                    'ifDescr': val
                }
            self.data['idx'] = self.data['idx'].astype('object')
            self.data.set_index('idx', inplace=True)
        except Exception as e:
            print(f"[-][{self.dt_now}][{self.hostname}]: Error during SNMP walk Alias: {e}")

    async def walk_ifName(self):
        time.sleep(1)
        try:
            print(f"[.][{self.dt_now}][{self.hostname}]: Getting interfaces' Name")
            async for req_oid, val in self.client.walk(".1.3.6.1.2.1.2.2.1.2"):
                self.data.loc[req_oid.split('.')[-1], 'ifName'] = val
        except Exception as e:
            print(f"[-][{self.dt_now}][{self.hostname}]: Error during SNMP walk Name: {e}")

    async def walk_ifSpeed(self):
        time.sleep(1)
        try:
            print(f"[.][{self.dt_now}][{self.hostname}]: Getting interfaces' Speed")
            async for req_oid, val in self.client.walk(".1.3.6.1.2.1.2.2.1.5"):
                self.data.loc[req_oid.split('.')[-1], 'ifSpeed'] = val
        except Exception as e:
            print(f"[-][{self.dt_now}][{self.hostname}]: Error during SNMP walk Speed: {e}")

    async def walk_ifAdminStatus(self):
        time.sleep(1)
        try:
            print(f"[.][{self.dt_now}][{self.hostname}]: Getting interfaces' AdminStatus")
            async for req_oid, val in self.client.walk(".1.3.6.1.2.1.2.2.1.7"):
                self.data.loc[req_oid.split('.')[-1], 'ifAdminStatus'] = val
        except Exception as e:
            print(f"[-][{self.dt_now}][{self.hostname}]: Error during SNMP walk AdminStatus: {e}")

    async def walk_ifOperStatus(self):
        time.sleep(1)
        try:
            print(f"[.][{self.dt_now}][{self.hostname}]: Getting interfaces' OperStatus")
            async for req_oid, val in self.client.walk(".1.3.6.1.2.1.2.2.1.8"):
                self.data.loc[req_oid.split('.')[-1], 'ifOperStatus'] = val
        except Exception as e:
            print(f"[-][{self.dt_now}][{self.hostname}]: Error during SNMP walk OperStatus: {e}")

    async def walk_ifHCInOctets(self):
        time.sleep(1)
        try:
            print(f"[.][{self.dt_now}][{self.hostname}]: Getting interfaces' HCInOctets")
            # async for req_oid, val in self.client.walk(".1.3.6.1.2.1.2.2.1.10"):
            async for req_oid, val in self.client.walk(".1.3.6.1.2.1.31.1.1.1.6"):
                self.data.loc[req_oid.split('.')[-1], 'ifHCInOctets'] = val
                self.t_in = time.time()
        except Exception as e:
            print(f"[-][{self.dt_now}][{self.hostname}]: Error during SNMP walk HCInOctets: {e}")

    async def walk_ifHCOutOctets(self):
        time.sleep(1)
        try:
            print(f"[.][{self.dt_now}][{self.hostname}]: Getting interfaces' HCOutOctets")
            # async for req_oid, val in self.client.walk(".1.3.6.1.2.1.2.2.1.16"):
            async for req_oid, val in self.client.walk(".1.3.6.1.2.1.31.1.1.1.10"):
                self.data.loc[req_oid.split('.')[-1], 'ifHCOutOctets'] = val
                self.t_out = time.time()
        except Exception as e:
            print(f"[-][{self.dt_now}][{self.hostname}]: Error during SNMP walk HCOutOctets: {e}")

    async def walk_jnxDomCurrentRxLaserPower(self):
        time.sleep(1)
        try:
            print(f"[.][{self.dt_now}][{self.hostname}]: Getting interfaces' CurrentRxLaserPower")
            async for req_oid, val in self.client.walk(".1.3.6.1.4.1.2636.3.60.1.1.1.1.5"):
                self.data.loc[req_oid.split('.')[-1], 'jnxDomCurrentRxLaserPower'] = val
        except Exception as e:
            print(f"[-][{self.dt_now}][{self.hostname}]: Error during SNMP walk CurrentRxLaserPower: {e}")

    async def walk_jnxDomCurrentRxLaserPowerHighWarningThreshold(self):
        time.sleep(1)
        try:
            print(f"[.][{self.dt_now}][{self.hostname}]: Getting interfaces' CurrentRxLaserPowerHighWarningThreshold")
            async for req_oid, val in self.client.walk(".1.3.6.1.4.1.2636.3.60.1.1.1.1.11"):
                self.data.loc[req_oid.split('.')[-1], 'jnxDomCurrentRxLaserPowerHighWarningThreshold'] = val
        except Exception as e:
            print(f"[-][{self.dt_now}][{self.hostname}]: Error during SNMP walk CurrentRxLaserPowerHighWarningThreshold: {e}")

    async def walk_jnxDomCurrentRxLaserPowerLowWarningThreshold(self):
        time.sleep(1)
        try:
            print(f"[.][{self.dt_now}][{self.hostname}]: Getting interfaces' CurrentRxLaserPowerLowWarningThreshold")
            async for req_oid, val in self.client.walk(".1.3.6.1.4.1.2636.3.60.1.1.1.1.12"):
                self.data.loc[req_oid.split('.')[-1], 'jnxDomCurrentRxLaserPowerLowWarningThreshold'] = val
        except Exception as e:
            print(f"[-][{self.dt_now}][{self.hostname}]: Error during SNMP walk CurrentRxLaserPowerLowWarningThreshold: {e}")

    @staticmethod
    def traffic_calc(ifHCInOctets_1, t1, ifHCInOctets_2, t2):
        if ifHCInOctets_2 >= ifHCInOctets_1:
            result = ((ifHCInOctets_2 - ifHCInOctets_1)*8)/(t2 - t1)
        else:
            # return ((4_294_967_295 - ifHCInOctets_1) + ifHCInOctets_2 + 1)/(t2 - t1)
            result = (((18_446_744_073_709_551_615 - ifHCInOctets_1) + ifHCInOctets_2 + 1)*8)/(t2 - t1)
        return round(result)

    def cleanData(self):
        self.data = self.data[self.data['ifDescr'] != b'']
        self.data['ifDescr'] = self.data['ifDescr'].str.decode('utf-8', errors='replace')
        self.data['ifName'] = self.data['ifName'].str.decode('utf-8', errors='replace')
        self.data['ifSpeed'] = self.data['ifSpeed'].astype(int)
        self.data['jnxDomCurrentRxLaserPower'] = self.data['jnxDomCurrentRxLaserPower']*0.01
        self.data['jnxDomCurrentRxLaserPower'] = self.data['jnxDomCurrentRxLaserPower'].round(2)
        self.data['jnxDomCurrentRxLaserPowerLowWarningThreshold'] = self.data['jnxDomCurrentRxLaserPowerLowWarningThreshold']*0.01
        self.data['jnxDomCurrentRxLaserPowerLowWarningThreshold'] = self.data['jnxDomCurrentRxLaserPowerLowWarningThreshold'].round(2)
        self.data['jnxDomCurrentRxLaserPowerHighWarningThreshold'] = self.data['jnxDomCurrentRxLaserPowerHighWarningThreshold']*0.01
        self.data['jnxDomCurrentRxLaserPowerHighWarningThreshold'] = self.data['jnxDomCurrentRxLaserPowerHighWarningThreshold'].round(2)
        status_map = {1: "up", 2: "down"}
        self.data['ifAdminStatus'] = self.data['ifAdminStatus'].map(status_map).fillna("testing")
        self.data['ifOperStatus'] = self.data['ifOperStatus'].map(status_map).fillna("testing")

    @staticmethod
    def saveFileInJson(file_name, data):
        with open(file_name, 'w') as f:
            json.dump(data, f)

    def es_createIndex(self):
        mappings = {
            "properties": {
                "@timestamp": {"type": "date"},
                "sysInfo": {
                    "properties": {
                        "name": {"type": "text"},
                        "uptime": {"type": "unsigned_long"},
                        "temperature": {"type": "short"},
                        "cpu": {"type": "short"},
                        "ram": {"type": "short"}
                    }
                },
                "alarm": {
                    "properties": {
                        "yellow_state":  {"type": "keyword"},
                        "yellow_count":  {"type": "integer"},
                        "yellow_lastChange":  {"type": "unsigned_long"},
                        "red_state":  {"type": "keyword"},
                        "red_count":  {"type": "integer"},
                        "red_lastChange":  {"type": "unsigned_long"},
                    }
                },
                "if": {
                    "type": "nested",
                    "dynamic": False,
                    "include_in_root": True,
                    "properties": {
                        "name": {"type": "keyword"},
                        "description": {"type": "text"},
                        "speed": {"type": "unsigned_long"},
                        "traffic_inbound": {"type": "long"},
                        "traffic_outbound": {"type": "long"},
                        "status_admin": {"type": "keyword"},
                        "status_oper": {"type": "keyword"},
                        "RX_laser_power": {"type": "float"},
                        "RX_laser_power_warning_high": {"type": "float"},
                        "RX_laser_power_warning_low": {"type": "float"}
                    }
                }
            }
        }
        settings = {
            "number_of_shards": 1,
            "number_of_replicas": 1
        }
        if self.esClient.indices.exists(index=f"{self.index_name}"):
            print(f"[*][{self.dt_now}][{self.hostname}]: Index {self.index_name} is already existed - Pass")
        else:
            self.esClient.indices.create(
                index=f"{self.index_name}",
                mappings=mappings,
                settings=settings
            )
            print(f"[+][{self.dt_now}][{self.hostname}]: Index {self.index_name} created")

    def es_sendData(self, data_key, data_val, data_id=None):
        if not data_id:
            data_id = int(self.dt_now.timestamp())
        data_req = {
            "@timestamp": self.dt_now.isoformat()+"Z",
            data_key: data_val,
        }
        self.esClient.index(index=f"{self.index_name}", document=data_req, id=data_id)

    def saveDataSys(self):
        data_item = {
            "name": self.sys_name,
            "uptime": self.sys_uptime,
            "descr": self.sys_descr,
            "temperature": self.sys_temp,
            "cpu": self.sys_cpu,
            "ram": self.sys_ram
        }
        self.es_sendData("sysInfo", data_item, 1)
        print(f"[+][{self.dt_now}][{self.hostname}]: Upload data[sysInfo] successfully")

    def saveDataAlarm(self):
        data_item = {
            "yellow_state": self.yellow_state,
            "yellow_count": self.yellow_count,
            "yellow_lastChange": self.yellow_lastChange,
            "red_state": self.red_state,
            "red_count": self.red_count,
            "red_lastChange": self.red_lastChange
        }
        self.es_sendData("alarm", data_item, 2)
        print(f"[+][{self.dt_now}][{self.hostname}]: Upload data[alarm] successfully")

    def saveDataIf(self):
        data_if = []
        for row in self.data.itertuples():
            data_item = {
                "name": row[1],
                "description": row[2],
                "speed": row[3],
                "status_admin": row[4],
                "status_oper": row[5],
                "traffic_inbound": row[6],
                "traffic_outbound": row[7],
            }
            if pd.notna(row[8]):
                data_item['RX_laser_power'] = row[8]
            if pd.notna(row[9]):
                data_item['RX_laser_power_warning_high'] = row[9]
            if pd.notna(row[10]):
                data_item['RX_laser_power_warning_low'] = row[10]
            data_if.append(data_item)
        self.es_sendData("if", data_if)
        self.data[['ifHCInOctets', 'ifHCOutOctets']].to_csv(f'./output/temp.{self.hostname}.csv')
        print(f"[+][{self.dt_now}][{self.hostname}]: Upload data[interface] successfully")

    async def gather_data(self):
        check = await self.check_connection()
        if check:
            await self.get_sysInfo()
            await self.get_alarm()
            await self.walk_ifAlias()
            await self.walk_ifName()
            await self.walk_ifSpeed()
            await self.walk_ifAdminStatus()
            await self.walk_ifOperStatus()
            await self.walk_ifHCInOctets()
            await self.walk_ifHCOutOctets()
            await self.walk_jnxDomCurrentRxLaserPower()
            await self.walk_jnxDomCurrentRxLaserPowerHighWarningThreshold()
            await self.walk_jnxDomCurrentRxLaserPowerLowWarningThreshold()
            print(f"[+][{self.dt_now}][{self.hostname}]: Gathering SNMP info successfully")

    def run(self):
        os.makedirs("./output", exist_ok=True)
        self.loadPrevData()
        asyncio.run(self.gather_data())
        self.cleanData()
        self.es_createIndex()
        self.saveDataSys()
        self.saveDataAlarm()
        self.saveDataIf()


if __name__ == "__main__":
    pass
