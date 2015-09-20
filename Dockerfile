FROM python:2.7
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

ENV RACONTEUR_CONFIG_FILE="/usr/src/app/config.py"
ENV BRANCH="master"
ENV DOMAIN="helmgast.se"

RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python start.py"]