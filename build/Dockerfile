# set base image (host OS)
FROM python:3.6-slim-stretch

# set the working directory in the container
WORKDIR /service

# copy the dependencies file to the working directory
COPY requirements.txt .

# install dependencies
RUN apt-get update -y \
    && apt-get install -y build-essential default-libmysqlclient-dev vim \
    && pip install -r requirements.txt \
    && apt-get autoremove -y && apt-get autoclean -y \
    && rm -rf /usr/local/src/*

# copy the content of the local src directory to the working directory
COPY ./ .

# command to run on container start
CMD ["python", "./run.py"]
