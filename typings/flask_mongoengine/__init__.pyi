import mongoengine
from mongoengine.queryset import QuerySet
from typing import Any, Optional

VERSION: Any


def get_version():
    ...


def current_mongoengine_instance():
    ...


class MongoEngine:
    app: Any = ...
    Document: Any = ...
    DynamicDocument: Any = ...

    def __init__(self, app: Optional[Any] = ..., config: Optional[Any] = ...) -> None:
        ...

    def init_app(self, app: Any, config: Optional[Any] = ...) -> None:
        ...

    @property
    def connection(self):
        ...


class BaseQuerySet(QuerySet):
    def get_or_404(self, *args: Any, **kwargs: Any):
        ...

    def first_or_404(self):
        ...

    def paginate(self, page: Any, per_page: Any, **kwargs: Any):
        ...

    def paginate_field(self, field_name: Any, doc_id: Any, page: Any, per_page: Any, total: Optional[Any] = ...):
        ...


class Document(mongoengine.Document):
    meta: Any = ...

    def paginate_field(self, field_name: Any, page: Any, per_page: Any, total: Optional[Any] = ...):
        ...


class DynamicDocument(mongoengine.DynamicDocument):
    meta: Any = ...
