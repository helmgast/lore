FROM python:2.7

MAINTAINER Ripperdoc

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt run.py /usr/src/app/
RUN pip install --no-cache-dir -r requirements.txt
COPY tools/ tools/
COPY fablr/ fablr/
COPY static/ static/

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