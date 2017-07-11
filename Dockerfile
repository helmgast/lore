# First stage - build static resources using node. Required Docker CE >=17.06
FROM node:latest
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
COPY assets/ assets/
COPY static/ static/
COPY package.json .
COPY webpack.config.js .
RUN npm install
RUN npm run build

# Second stage, copy over static resources and start the python
FROM python:2.7
MAINTAINER Ripperdoc
WORKDIR /usr/src/app
COPY --from=0 /usr/src/app/static/ static/
COPY requirements.txt run.py /usr/src/app/
RUN pip install --no-cache-dir -r requirements.txt
COPY tools/ tools/
COPY fablr/ fablr/

ENV FLASK_APP=run.py
RUN flask lang_compile

# provide from git or by Docker autobild
ARG SOURCE_COMMIT=no_ver
# provide from git or by Docker autobild
ARG SOURCE_BRANCH=no_branch
ENV FABLR_VERSION ${SOURCE_BRANCH}-${SOURCE_COMMIT}
RUN echo \$FABLR_VERSION=${FABLR_VERSION}

# This format runs executable without bash/shell, faster
CMD ["python","run.py"]