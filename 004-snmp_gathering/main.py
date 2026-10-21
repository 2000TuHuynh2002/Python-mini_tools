#!/usr/bin/env python3

import yaml
import subprocess
import threading
import time



HOSTS_FILE = "hosts.yml"
RUNNING_PROCESS = {}
INTERVAL = 300



def call_pyshell(info):
    RUNNING_PROCESS[info['name']] = ["[.]", 0]
    while True:
        try:
            start_time = time.time()
            command = f'python3 local_pyshell.py {info['host']} {info['port']} {info['community']} {info['name']}'
            result = subprocess.run(command.split(' '))
            end_time = time.time()

            if result.returncode == 0:
                RUNNING_PROCESS[info['name']] = ["[+]", round(end_time - start_time, 4)]
            else:
                RUNNING_PROCESS[info['name']] = ["[-]", round(end_time - start_time, 4)]
                
        except:
            RUNNING_PROCESS[info['name']] = ["[x]", 0]
        time.sleep(INTERVAL)


def report_schedule():
    while True:
        print(f"[*] Reporting: detect {len(RUNNING_PROCESS)} devices")
        with open("snmp_report.txt", "w") as f:
            for k, val in RUNNING_PROCESS.items():
                f.write(f"{val[0]} {k}: {val[1]}s\n")
        time.sleep(60)


def run_snmp_gathering():
    threads = []
    try:
        with open(HOSTS_FILE, 'r') as file:
            devices_info = yaml.safe_load(file)
        for info in devices_info['snmp']:
            t_shell = threading.Thread(target=call_pyshell, args=(info,))
            threads.append(t_shell)
        t_report = threading.Thread(target=report_schedule)
        threads.append(t_report)
        for t in threads:
            t.start()
    except FileNotFoundError:
        print(f"[x] System: {HOSTS_FILE} not found.")
    except yaml.YAMLError as exc:
        print(f"[x] System: Error parsing YAML: {exc}")


if __name__ == "__main__":
    run_snmp_gathering()
