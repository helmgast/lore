from celery import Celery, task


def make_celery(flask_app):
  if not flask_app or not flask_app.config['CELERY_BROKER_URL']:
    return {}
  celery = Celery(flask_app.import_name, broker=flask_app.config['CELERY_BROKER_URL'])
  celery.conf.update(flask_app.config)
  TaskBase = celery.Task

  class ContextTask(TaskBase):
    abstract = True

    def __call__(self, *args, **kwargs):
      with flask_app.app_context():
        return TaskBase.__call__(self, *args, **kwargs)

  celery.Task = ContextTask

  @task
  def fetch_pdf_eon_cf(x, y):
    return x + y

  # celery.fetch_pdf_eon_cf = fetch_pdf_eon_cf

  print 'Registered tasks: %s' % celery.tasks.keys()
  return celery
