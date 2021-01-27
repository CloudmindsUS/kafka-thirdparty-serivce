# for kakfa-thirdparty serivce on GCPV3.3 prod env

To build docker container:

1. `cp database.csv __config__.py Dockerfile requirements.txt run.py start.sh kakfa-thirdparty-service/`  
2. Add Twilio info to `__config__.py` and save  
3. `docker build -t harbor.cloudminds.com/kafka-thirdparty/service:Vx.x`  
