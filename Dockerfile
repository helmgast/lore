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
FROM python:3.6-alpine
RUN apk update && apk upgrade && apk add --no-cache bash git openssh zlib-dev jpeg-dev gcc musl-dev libmagic curl
# Temporarily install pipenv from nightly
RUN set -ex && pip install git+git://github.com/pypa/pipenv.git@8378a1b104f2d817790a05da370bef0a1b00f452
LABEL maintainer="martin@helmgast.se"
WORKDIR /usr/src/app
COPY --from=0 /usr/src/app/static/ static/
COPY Pipfile Pipfile.lock run.py /usr/src/app/
RUN pipenv install --system
COPY tools/ tools/
COPY fablr/ fablr/
COPY plugins/ plugins/

ENV FLASK_APP=run.py
RUN flask lang_compile

# provide from git or by Docker autobild
ARG SOURCE_COMMIT=no_ver
# provide from git or by Docker autobild
ARG SOURCE_BRANCH=no_branch
ENV FABLR_VERSION ${SOURCE_BRANCH}-${SOURCE_COMMIT}
RUN echo \$FABLR_VERSION=${FABLR_VERSION}

# This format runs executable without bash/shell, faster
CMD ["flask","run"]