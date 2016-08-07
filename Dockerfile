#FROM frolvlad/alpine-python2
FROM python:2.7

MAINTAINER Ripperdoc

# Will add necessary libraries to Alpine, mostly do be able to use Pillow image library
#RUN apk update && apk upgrade && \
#    apk add --no-cache bash git openssh jpeg-dev zlib-dev g++ python-dev libmagic
#ENV LIBRARY_PATH=/lib:/usr/lib

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY tools/ tools/
COPY fablr/ fablr/
COPY manage.py manage.py
COPY run.py run.py

RUN python manage.py lang_compile

ARG FABLR_VERSION=noversion
ENV FABLR_VERSION $FABLR_VERSION
ENTRYPOINT python run.py
