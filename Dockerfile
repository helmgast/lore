# First stage - build static resources using node. Required Docker CE >=17.06
FROM node:latest
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
COPY assets/ assets/
COPY static/ static/
COPY package.json package-lock.json /usr/src/app/
COPY webpack.config.js .
RUN npm install
RUN npm run build

# Second stage, copy over static resources and start the python
FROM python:3.9-alpine
RUN apk update && apk upgrade && apk add --no-cache bash git openssh zlib-dev jpeg-dev gcc musl-dev libmagic curl tar
LABEL maintainer="martin@helmgast.se"
EXPOSE 5000
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV FLASK_APP=run.py

WORKDIR /usr/src/app
COPY --from=0 /usr/src/app/static/ static/
COPY requirements.txt run.py /usr/src/app/
RUN pip install -r requirements.txt
COPY tools/ tools/
COPY lore/ lore/
COPY plugins/ plugins/
COPY config.py config.py

RUN flask lang-compile

CMD gunicorn -b :5000 run:app