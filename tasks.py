from celery import Celery
from flask import current_app


def make_celery(flask_app):
  celery = Celery(flask_app.import_name, broker=flask_app.config['CELERY_BROKER_URL'])
  celery.conf.update(flask_app.config)
  TaskBase = celery.Task

  class ContextTask(TaskBase):
    abstract = True

    def __call__(self, *args, **kwargs):
      with flask_app.app_context():
        return TaskBase.__call__(self, *args, **kwargs)

  celery.Task = ContextTask
  return celery


celery = make_celery(current_app)


@celery.task
def fetch_pdf_eon_cf(x, y):
  return x + y