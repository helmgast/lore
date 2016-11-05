FROM python:2.7

MAINTAINER Ripperdoc

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY tools/ tools/
COPY fablr/ fablr/
COPY manage.py manage.py
COPY run.py run.py
RUN python manage.py lang_compile

ENV SOURCE_COMMIT $SOURCE_COMMIT
CMD ["python","run.py"] # This format runs executable without bash/shell