#! /usr/bin python3

import pandas as pd
from kafka import KafkaConsumer
from kafka import TopicPartition
import json
import time
import logging
import requests
import base64
from twilio.rest import Client
import math

import __config__ as config
from datetime import datetime
import datetime as dt

import face_recognition
from face_recognition import load_image_file, face_encodings, compare_faces

import os
import urllib.request

if os.path.exists('temp.jpg'):
    os.remove('temp.jpg')

requests.adapters.DEFAULT_RETRIES = 15
thres = 97
s = requests.session()
s.keep_alive = False

day_record = datetime.now()-dt.timedelta(hours = 8)
time_zone = {'Pacific':8, 'Mountain':7, 'Central':6, 'Eastern':5}

logging.basicConfig(level=logging.WARNING,
                    filename='log/CITMS50.log',
                    filemode='a',
                    format='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s'
                    )

def formulation(client_id, username, password):
    base64string = base64.b64encode('%s:%s' % (username, password))
    authheader =  "Basic %s" % base64string
    headers = {"Authorization": authheader , "Content-Type": "application/json"}
    url = 'https://api.mydevices.com/things/' + client_id + '/data'
    return url, headers


df = pd.read_csv('database.csv', delimiter = ',', skiprows=1, names = ['Device_Name', 'IMEI', 'Device_ID', 'Name1', 'contact1', 'Name2', 'contact2', 'Name3', 'contact3', 'threshold', 'interval', 'TimeZone'], index_col='IMEI')
print(df)
consumer = KafkaConsumer(bootstrap_servers=[config.server_ip])
# consumer = KafkaConsumer(bootstrap_servers=[config.server_ip], auto_offset_reset='earliest')
consumer.subscribe(topics=(config.kafka_topic)) 
print (consumer.subscription())
print (consumer.assignment())

time_history = {}

while True:
    msg = consumer.poll(timeout_ms=1000) 
    if bool(msg):
        # print(msg)
        logging.info(msg)
        
        df = pd.read_csv('database.csv', delimiter = ',', skiprows=1, names = ['Device_Name', 'IMEI', 'Device_ID', 'Name1', 'contact1', 'Name2', 'contact2', 'Name3', 'contact3', 'threshold', 'interval', 'TimeZone'], index_col='IMEI')

        curr_date = datetime.now()-dt.timedelta(hours = 8)
        if day_record.day != curr_date.day or day_record.month != curr_date.month:
            time_history = {}
            day_record = curr_date
            

        all_data = msg.get(TopicPartition(topic=u'detect_record', partition=0))
        # print(all_data)
        for each in all_data:
            
            tmp = eval(each.value)
            # print(time_history)
            # print(each)

            curr_device = tmp.get('device_id')
            #print(df.index.values.tolist())
            #print(curr_device in df.index.values.tolist())

            if curr_device in df.index.values.tolist():
            
                interval = 8000
                if math.isnan(df['interval'][curr_device]):
                    interval = 8000
                else:
                    interval = df['interval'][curr_device]*1000
                    
                if os.path.exists('temp.jpg'):
                    os.remove('temp.jpg')

                
                urllib.request.urlretrieve(tmp.get('face_url'), 'temp.jpg')
                

                if curr_device not in time_history:
                    print('not in time history')
                    tmp_o = load_image_file('temp.jpg');
                    tmp_e = face_encodings(tmp_o);
                    if tmp_e != []:
                        time_history[curr_device] = [tmp_e[0], each.timestamp, 1]
                        result = True
                    else:
                        continue
                else:
                    print('in time history')
                    if each.timestamp - time_history[curr_device][1]>interval:
                        tmp_o = load_image_file('temp.jpg');
                        tmp_e = face_encodings(tmp_o);
                        count = time_history[curr_device][2]
                        if tmp_e != []:
                            time_history[curr_device] = [tmp_e[0], each.timestamp, count+1]
                            result = True
                        else:
                            continue
                    else:    
                        prev_e = time_history[curr_device][0]
                        now = load_image_file('temp.jpg');
                        now_e = face_encodings(now);
                        if now_e == []:
                            continue
                        try:
                            result = compare_faces([prev_e], now_e[0])[0];
                            result = bool(result)
                            print(result)
                        except:
                            print(len(now_e),len(prev_e))
                            print('exception')
                            result = True
                    
                        #except:
                        #    print('err')
                        #    continue
                        
                        if result == True:
                            print('result ok', time_history[curr_device][2])
                            time_history[curr_device][1] = each.timestamp
                            continue
                        else:
                            count = time_history[curr_device][2]+1
                            print('result not ok', time_history[curr_device][2])
                            time_history[curr_device] = [now_e[0], each.timestamp, count]

                if tmp.get('temperature')*1.8+32 < 95 or tmp.get('temperature')*1.8+32 > 105:
                    continue

                thres = float(df['threshold'][curr_device])
            

                data = [{
                        # "channel": tmp.get('device_id'),
                        "channel": 1,
                        "value": tmp.get('temperature')*1.8+32,
                        "type": "temp",
                        "unit": "f"
                }]
                
                # print(str(data) + ' IMEI: ' + tmp.get('device_id'))
                

                if isinstance(df['TimeZone'][curr_device],float):
                    tz = 'Pacific'
                else:
                    tz = df['TimeZone'][curr_device]


                eui = df['Device_ID'][curr_device]

                if eui != '0':
                    data_iot = {
                            'eui': eui,
                            'format': 'json',
                            'data': {
                                'payload': 
                                    [
                                        {
                                            "channel":1,
                                            "value":tmp.get('temperature')*1.8+32,
                                            "type": "temp",
                                            "unit": "f",
                                            "name": "Wright Gatekeeper"
                                        },
                                        {
                                            "channel":2,
                                            "value":time_history[curr_device][2],
                                            "type": "counter",
                                            "name": "Daily_Count"
                                        }
                                    ]    
                                    
                                }
                            }
                    r = requests.post(url = "https://lora.iotinabox.com/v1/networks/iotinabox/uplink",data=json.dumps(data_iot))
                    print(r, data_iot)
                    logging.info(data_iot)


                # http_url, http_headers = formulation(
                #         df.loc[[ind]].Client_id.values.tolist()[0],
                #         df.loc[[ind]].Username.values.tolist()[0],
                #         df.loc[[ind]].Password.values.tolist()[0]) 
                account_sid = 'ACcfc2242432d092ac2e7f568f2599218b'
                auth_token = 'a32f2f23cd43a7d83af11b6d6b24575e'
                client = Client(account_sid, auth_token)


                # device_id = df.loc[[ind]].Device_ID.values.tolist()[0]
                # print(list(alert_contact.index))

                

                if float(tmp.get('temperature'))*1.8+32> thres:
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
                    for contact in contacts:
                        dt_now = datetime.now()-dt.timedelta(hours=time_zone[tz])
                        msg_body = 'Hi ' + contact[1] + ', Your Gatekeeper Device ending in ' + tmp.get('device_id')[-5:] + ' has detected a High Temperature of ' + str(tmp.get('temperature')*1.8+32) + ' F at ' + datetime.strftime(dt_now, '%Y-%m-%d %H:%M:%S') + '. Device ID: ' + tmp.get('device_id')

                        message = client.messages.create(
                                body=msg_body,
                                from_='+16066209564',
                                to='+1'+str(contact[0])
                                )
                        print(message.sid, contact, msg_body)
                        logging.info(message)
                
                # try:       
                #     r = requests.post(url = http_url, 
                #                       data = json.dumps(data), 
                #                       headers = http_headers)
                #     time.sleep(0.25) 
                #     if r.status_code == 200:
                #         print ('Data sent successfully with IMEI: ' + tmp.get('device_id'))
                #         logging.warn('Data sent successfully with IMEI: ' + tmp.get('device_id'))
                #     else:
                #         print ('Request received ' + str(r.status_code) + ' with IMEI: ' + tmp.get('device_id'))
                #         logging.warn('Request received ' + str(r.status_code) + ' with IMEI: ' + tmp.get('device_id'))
                #     r.close()
                #     del(r) 
                # 
                # except Exception as e:
                #     # print e
                #     logging.warn(e)
                #     time.sleep(10)
                #     continue

            else: 
                logging.warn(' No corresponding account with IMEI: ' + tmp.get('device_id'))
                continue            
        
    else:
        print('-')
        print('--')
        time.sleep(1) 
        continue
