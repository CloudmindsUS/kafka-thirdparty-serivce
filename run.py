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

# For Initialization Kafka
def init():
    engine = create_engine(config.mysql_conf, echo=False)
    if not database_exists(engine.url):
        create_database(engine.url)
    df = pd.read_csv('database.csv', delimiter=',', skiprows=1, names=['Device_Name', 'IMEI', 'Device_ID', 'Name', 'Contact'])
    df.to_sql('infos', if_exists='replace', con=engine)
    print(df)
    
    df_new = pd.read_sql_table('infos', config.mysql_conf, index_col='IMEI')
    df_new = df_new.drop(columns=['index'])     
    print(df_new)

    return

# Singe Loop
def loop_once(msg, time_zone):
    print(msg)
    df = pd.read_sql_table('infos', config.mysql_conf, index_col='IMEI')
    df = df.drop(columns=['index'])
    all_data = sum(msg.values(), [])
    
    for each in all_data:    
        tmp = eval(each.value)
        curr_device = str(tmp.get('device_id'))
        device_list = df.index.values.tolist()
        print(type(curr_device), device_list)

        if curr_device not in device_list:
            print('No corresponding account with IMEI: ' + tmp.get('device_id'))
            continue
        try:
            process_each_data(tmp, df, time_zone, each, curr_device)
        except:
            print('Twilio Error')

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

    thres = tmp.get('threshold')
    tz = tmp.get('timezone')
    eui = df['Device_ID'][curr_device]

    if eui != '0' and eui != 0:
        send_iot_payload(tmp, eui, curr_device)

    auth_df = pd.read_sql_table('auth',config.mysql_conf)
    sid = auth_df['sid'][0]
    token = auth_df['token'][0]
    phone = auth_df['phone'][0]
    
    checkin_url = auth_df['url'][0]
    param = {'deviceID': int(tmp.get('device_id'))}

    client = Client(sid, token)


    if tmp.get('f_temperature') > thres:
        
        name_str = df['Name'][curr_device]
        contact_str = df['Contact'][curr_device]
        if name_str is None or contact_str is None:
            return
        names = name_str.split(',')
        contacts = contact_str.split(',')
        
        if tmp.get('mask') == 1:
            substring = 'with mask'
        elif tmp.get('mask') == 2:
            substring = 'without mask'
        elif tmp.get('mask') == 0:
            substring = ''
            
        r = None
        try:
            r = requests.get(checkin_url,param).json()
        except:
            print('Check in checkout failed')
        
        try:
            if r is not None and r['data'] != '':
                print('CheckMe Message')
                if abs(datetime.timestamp(datetime.now())-int(r['time'])) < 10:
                    for contact in contacts:
                        dt_now = datetime.now() - dt.timedelta(hours=time_zone[tz])
                        msg_body = 'Hi, ' + r['data'] + ' has a High Temperature of ' + str(tmp.get('f_temperature')) + ' F ' + substring + ' at ' + datetime.strftime(dt_now, '%Y-%m-%d %H:%M:%S') + '. Device ID: ' + tmp.get('device_id')
            
                        message = client.messages.create(body=msg_body, from_=phone, to='+1'+contact)
                        print(message.sid, contact, msg_body)
                    
                else:
                    print('Time too long', abs(datetime.timestamp(datetime.now())-int(r['time'])))
        except:
            print('Data error')
        
        for i, contact in enumerate(contacts):
        
            print('Normal Message')
            dt_now = datetime.now() - dt.timedelta(hours=time_zone[tz])
            
            if tmp.get('name') == '':
                msg_body = 'Hi ' + names[i] + ', Your Gatekeeper Device ending in ' + tmp.get('device_id')[-5:] + ' has detected a High Temperature of ' + str(tmp.get('f_temperature')) + ' F ' + substring + ' at ' + datetime.strftime(dt_now, '%Y-%m-%d %H:%M:%S') + '. Device ID: ' + tmp.get('device_id')
            else:
                msg_body = 'Hi, ' + tmp.get('name') + ' has a High Temperature of ' + str(tmp.get('f_temperature')) + ' F ' + substring + ' at ' + datetime.strftime(dt_now, '%Y-%m-%d %H:%M:%S') + '. Device ID: ' + tmp.get('device_id')
            
            message = client.messages.create(body=msg_body, from_=phone, to='+1'+contact)
            print(message.sid, contact, msg_body)

if __name__ == "__main__":
    consumer = KafkaConsumer(bootstrap_servers=[config.server_ip])
    topics = list(consumer.topics())
    valid_topics = [topic for topic in topics if topic[:13]=='detect_record']
    consumer.subscribe(valid_topics)
    time_zone = {'America/Midway':11, 'America/Honolulu':10, 'America/Los_Angeles':7, 'America/Phoenix':7, 'America/Denver': 6, 'America/Chicago':5, 'America/New_York':4}
    print (consumer.subscription())
    print (consumer.assignment())

    # init()

    while True:
        msg = consumer.poll(timeout_ms=1000) 
        if not bool(msg):
            time.sleep(1)
            continue
        loop_once(msg, time_zone)
