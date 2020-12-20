# FROM ubuntu:18.04

# RUN sudo apt-get update -y

# RUN apt-get -y install cmake

# set base image (host OS)
FROM python:3.6

# set the working directory in the container
WORKDIR /test

# copy the dependencies file to the working directory
COPY requirements.txt .

# install dependencies

RUN apt-get update -y

RUN apt-get -y install cmake

RUN pip install -r requirements.txt

# copy the content of the local src directory to the working directory
COPY ./ .

# command to run on container start
CMD [ "python", "./run.py" ]