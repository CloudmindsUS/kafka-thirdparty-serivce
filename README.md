# for kakfa-thirdparty serivce on GCPV3.3 prod env

To build docker container:

1. Add Twilio info to `__config__.py` and save  
2. `cp database.csv __config__.py run.py build/`  
3. `cd build`  
4. `docker build -t harbor.cloudminds.com/kafka-thirdparty/service:Vx.x . `  
