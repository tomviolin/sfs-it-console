#!/home/tomh/sfs-it-console/venv/bin/python3

import os
import sys
import cgitb
import cgi
import subprocess
import json
import re
import time
import datetime
import shutil
import logging
from ping3 import ping
import html
import requests
import base64
import urllib.parse
import matplotlib.pyplot as plt
import numpy as np
import sqlite3
import io
from PIL import Image
from io import BytesIO

# check various services on a number of servers and report back to the console
# this is a CGI script that is called from the console web page


# set up some globals

# red X image for errors in image checks
redX = open("redX.png", "rb").read()
redX = base64.b64encode(redX).decode('ascii')
redXurl = "data:image/png;base64," + redX
# set up logging
logging.basicConfig(filename='/home/tomh/sfs-it-console/logs/sfs-it-console.log', level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')

# set up cgitb
# cgitb.enable()

# try to read types parameter from CGI
try:
    form = cgi.FieldStorage()
    types = types
except:
    types = 'pdi'



# set up sqlite3
dbconn = sqlite3.connect('/home/tomh/sfs-it-console/sfs-it-console.db')
dbconn.row_factory = sqlite3.Row

dbconn.execute('''
    CREATE TABLE IF NOT EXISTS "ping" (
        "id" TEXT NOT NULL,
        "desc" TEXT NOT NULL,
        "host" TEXT NOT NULL,
        "status" TEXT NOT NULL, 
        "rtt_avg_ms" REAL NOT NULL, 
        "timestamp" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY("id","timestamp"));
''')

dbconn.execute('''
    CREATE TABLE IF NOT EXISTS "docker" (
        "id" TEXT NOT NULL,
        "desc" TEXT NOT NULL,
        "status" TEXT NOT NULL,
        "timestamp" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY("id","timestamp"));
''')

dbconn.execute('''
    CREATE TABLE IF NOT EXISTS "image" (
        "id" TEXT NOT NULL,
        "desc" TEXT NOT NULL,
        "dataurl" TEXT NOT NULL,
        "status" TEXT NOT NULL,
        "timestamp" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY("id","timestamp"));
''')


def ping_host(host):
    logging.debug('ping_host: ' + host)
    try:
        response_time = ping(host, timeout=8)
        logging.debug('response: ' + str(response_time))
        return response_time
    except:
        logging.debug('exception')
        return False



if __name__ == '__main__':
    print('Content-type: application/json\n\n')
    logging.debug('Content-type: application/json\n\n')
    config_file = '/home/tomh/sfs-it-console/config.json'
    config = None
    with open(config_file) as json_file:
        config = json.load(json_file)
    if config is None:
        logging.debug('config is None')
        sys.exit(1)
    
    all_responses = []
    ping_responses = []
    docker_responses = []
    image_responses = []

    if 'p' in types:
        for mon in config['ping']:
            
            logging.debug(f"mon: {mon['id']} {mon['host']} {mon['desc']}")
            ping_history = []
            c = dbconn.cursor()
            res = c.execute('''SELECT * from (
                SELECT substr(timestamp,1,19) minute, AVG(rtt_avg_ms) ping_time FROM ping WHERE id = ? GROUP BY minute ORDER BY minute DESC LIMIT 9
            ) order by minute asc''', (mon['id'],))
            for row in c.fetchall():
                ping_history = ping_history + [str(row['ping_time'])]

            response = ping_host(mon['host'])
            if response:
                response = round(response * 1000, 2)
                #print('{"status": "OK"}')
                logging.debug('{"status": "OK"}')
                #print(json.dumps(response, indent=4))
                ping_history = ping_history + [str(response)]
                ping_responses = ping_responses + [{"id": mon['id'], "desc":mon['desc'], "status": "OK","rtt_avg_ms": response, "history": ','.join(ping_history)}]
            else:
                #print('{"status": "ERROR"}')
                logging.debug('{"status": "ERROR"}')
                ping_history = ping_history + ["-1"]
                ping_responses = ping_responses + [{"id": mon['id'], "desc":mon['desc'], "status": "ERROR","rtt_avg_ms": -1, "history": ','.join(ping_history)}]
            c = dbconn.cursor()
            res = dbconn.execute('''
                INSERT OR IGNORE INTO ping (id, desc, host, status, rtt_avg_ms) VALUES (?, ?, ?, ?, ?)
            ''', (mon['id'], mon['desc'], mon['host'], ping_responses[-1]['status'], ping_responses[-1]['rtt_avg_ms']))

            dbconn.commit()
            c.close()


    if 'd' in types:
        for dcon in config['docker']:
         
            url = f'http://{dcon["host"]}:{dcon["apiport"]}/containers/json?filters={{"name": {json.dumps(dcon["name"])}}}'
            #print(url)
            filters = {"name": [f"{dcon['name'][0:1]}"]}
            logging.debug(f"url: {url}")
            logging.debug(f"filters: {filters}")
            try:
                response = requests.get(url)
            except:
                response = None

            if response is not None and response.status_code == 200 and len(response.json()) > 0:
                #print('{"status": "OK"}')
                logging.debug('{"status": "OK"}')
                docker_responses = docker_responses + [
                        {
                            "id": dcon['id'],
                            "name": dcon['name'],
                            "desc": dcon['desc'] + ":" +response.json()[0]['Status'],
                            "status": "OK"
                        }
                    ]
            else:
                #print('{"status": "ERROR"}')
                logging.debug('{"status": "ERROR"}')
                docker_responses = docker_responses + [
                        {
                            "id": dcon['id'], 
                            "name": dcon['name'],
                            "desc": dcon['desc'] + ":ERROR",
                            "status": "ERROR"
                        }
                    ]
            c = dbconn.cursor()
            params = (dcon['name'][0], dcon['desc'], docker_responses[-1]['status'])
            #print(params)
            res = c.execute('''
                INSERT OR IGNORE INTO docker (id, desc, status) VALUES (?, ?, ?)
            ''', params)
            dbconn.commit()
            c.close()


    if 'i' in types:
        for img in config['image']:
            url = img['url']
            logging.debug(f"url: {url}")
            try:
                response = requests.get(url,timeout=1)
            except:
                response = None
            if response is not None and response.status_code == 200:
                #print('{"status": "OK"}')
                logging.debug('{"status": "OK"}')
                im = Image.open(BytesIO(response.content))
                imwidth, imheight = im.size
                # make images 100px tall and set width to preserve aspect ratio
                imwid = int(100 * imwidth / imheight)
                im.thumbnail((imwid,100))
                buffered = BytesIO()
                im.save(buffered, format="PNG")
                data_url = base64.b64encode(buffered.getvalue()).decode('ascii')
                image_responses = image_responses + [{"id": img['id'], "desc": img['desc'], "url": url, "dataurl": "data:image/png;base64," + data_url, "status":"OK"}]
            else:
                #print('{"status": "ERROR"}')
                logging.debug('{"status": "ERROR"}')
                image_responses = image_responses + [{"id": img['id'], "desc": img['desc'], "dataurl": redXurl, "status":"ERROR"}]
            c = dbconn.cursor()
            res = c.execute('''
                INSERT OR IGNORE INTO image (id, desc, dataurl, status) VALUES (?, ?, ?, ?)
            ''', (img['id'], img['desc'], image_responses[-1]['dataurl'], image_responses[-1]['status']))
            dbconn.commit()
            c.close()

    responses = {"ping": ping_responses, "docker": docker_responses, "image": image_responses}

    print(json.dumps(responses, indent=4))
    sys.exit(0)

