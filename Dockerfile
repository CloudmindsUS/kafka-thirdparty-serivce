# set base image (host OS)
FROM python:3.6
MAINTAINER xin.li<xin.li@cloudminds.com>

# set the working directory in the container
WORKDIR /test

# copy the dependencies file to the working directory
COPY requirements.txt .

# install dependencies
RUN apt-get update -y \
    && apt install -y vim \
    && pip install -r requirements.txt

# copy the content of the local src directory to the working directory
COPY ./ .

# command to run on container start
CMD ["python", "./run.py"]
