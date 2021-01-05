#! /usr/bin python3

import pandas as pd
from kafka import KafkaConsumer
from kafka import TopicPartition
import json
import time
import requests
import base64
from twilio.rest import Client
import math

import __config__ as config
from datetime import datetime
import datetime as dt

import os
from urllib import request
import requests
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database

# For Initialization Kafka and Removing Temp Image
def init():
    engine = create_engine(config.mysql_conf,echo=False)
    if not database_exists(engine.url):
        create_database(engine.url)
    df = pd.read_csv('database.csv', delimiter=',', skiprows=1, names=['Device_Name', 'IMEI', 'Device_ID', 'Name1', 'contact1', 'Name2', 'contact2', 'Name3', 'contact3', 'threshold', 'interval', 'TimeZone'])
    df.to_sql('infos',if_exists='replace',con=engine)
    print(df)
    df_new = pd.read_sql_table('infos',config.mysql_conf, index_col='IMEI')
    df_new = df_new.drop(columns=['index'])     
    print(df_new)

    return

# Singe Loop
def loop_once(msg, time_zone):

    print(msg)
    df = pd.read_sql_table('infos', config.mysql_conf, index_col='IMEI')
    df = df.drop(columns=['index'])    
    #df = pd.read_csv('database.csv', delimiter = ',', skiprows=1, names = ['Device_Name', 'IMEI', 'Device_ID', 'Name1', 'contact1', 'Name2', 'contact2', 'Name3', 'contact3', 'threshold', 'interval', 'TimeZone'], index_col='IMEI')
        
    all_data = sum(msg.values(), [])
    
    for each in all_data:    
        tmp = eval(each.value)
        curr_device = str(tmp.get('device_id'))
        device_list = df.index.values.tolist()
        print(type(curr_device), device_list)

        if curr_device not in device_list:
            print('No corresponding account with IMEI: ' + tmp.get('device_id'))
            continue
        process_each_data(tmp, df, time_zone, each, curr_device)

def send_iot_payload(tmp, eui, curr_device):
    data_iot = {
        'eui': eui,
        'format': 'json',
        'data': {
            'payload': 
                [
                    {
                        "channel":1,
                        "value":tmp.get('f_temperature'),
                        "type": "temp",
                        "unit": "f",
                        "name": "Wright Gatekeeper"
                    }
                ]        
            }
        }
    r = requests.post(url = config.mydevices_url, data=json.dumps(data_iot))
    print(r, data_iot)


def process_each_data(tmp, df, time_zone, each, curr_device):

    if tmp.get('f_temperature') < config.lower_bound or tmp.get('f_temperature') > config.upper_bound:
        return

    thres = float(df['threshold'][curr_device])

    if isinstance(df['TimeZone'][curr_device],float):
        tz = 'Pacific'
    else:
        tz = df['TimeZone'][curr_device]


    eui = df['Device_ID'][curr_device]

    if eui != '0' and eui != 0:
        send_iot_payload(tmp,eui,curr_device)

    client = Client(config.account_sid, config.auth_token)

    if tmp.get('f_temperature')> thres:
        contacts = []
        name1 = df['Name1'][curr_device]
        name2 = df['Name2'][curr_device]
        name3 = df['Name3'][curr_device]
        contact1 = df['contact1'][curr_device]
        contact2 = df['contact2'][curr_device]
        contact3 = df['contact3'][curr_device]
        if contact1 is not None and math.isnan(contact1) is False:
            contacts.append([int(contact1),name1])
        if contact2 is not None and math.isnan(contact2) is False:
            contacts.append([int(contact2),name2])
        if contact3 is not None and math.isnan(contact3) is False:
            contacts.append([int(contact3),name3])
        if tmp.get('mask') == 1:
            substring = 'with mask'
        elif tmp.get('mask') == 2:
            substring = 'without mask'
        elif tmp.get('mask') == 0:
            substring = ''
        for contact in contacts:
            dt_now = datetime.now()-dt.timedelta(hours=time_zone[tz])
            if tmp.get('name') == '':
                msg_body = 'Hi ' + contact[1] + ', Your Gatekeeper Device ending in ' + tmp.get('device_id')[-5:] + ' has detected a High Temperature of ' + str(tmp.get('f_temperature')) + ' F ' + substring + ' at ' + datetime.strftime(dt_now, '%Y-%m-%d %H:%M:%S') + '. Device ID: ' + tmp.get('device_id')
            else:
                msg_body = 'Hi, ' + tmp.get('name') + ' has a High Temperature of ' + str(tmp.get('f_temperature')) + ' F ' + substring + ' at ' + datetime.strftime(dt_now, '%Y-%m-%d %H:%M:%S') + '. Device ID: ' + tmp.get('device_id')
            message = client.messages.create(
                    body=msg_body,
                    from_='+19169933295',
                    to='+1'+str(contact[0])
                    )
            print(message.sid, contact, msg_body)

if __name__ == "__main__":
    consumer = KafkaConsumer(bootstrap_servers=[config.server_ip])
    topics = list(consumer.topics())
    valid_topics = [topic for topic in topics if topic[:13]=='detect_record']
    consumer.subscribe(valid_topics)
    time_zone = {'Pacific':8, 'Mountain':7, 'Central':6, 'Eastern':5}
    print (consumer.subscription())
    print (consumer.assignment())

    init()

    while True:
        msg = consumer.poll(timeout_ms=1000) 
        if not bool(msg):
            time.sleep(1)
            continue
        loop_once(msg, time_zone)
