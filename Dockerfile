FROM python:2.7

MAINTAINER Ripperdoc

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY fablr/ fablr/
COPY run.py run.py

ENV RACONTEUR_CONFIG_FILE="/usr/src/app/config.py"
ENV BRANCH="master"
ENV DOMAIN="helmgast.se"

ENTRYPOINT python run.py