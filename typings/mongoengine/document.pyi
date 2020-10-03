from mongoengine.base import BaseDocument, DocumentMetaclass, TopLevelDocumentMetaclass
from mongoengine.queryset import NotUniqueError as NotUniqueError, OperationError as OperationError
from typing import Any, Optional


class InvalidCollectionError(Exception):
    ...


class EmbeddedDocument(BaseDocument, metaclass=DocumentMetaclass):
    my_metaclass: Any = ...
    __hash__: Any = ...

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        ...

    def __eq__(self, other: Any) -> Any:
        ...

    def __ne__(self, other: Any) -> Any:
        ...

    def to_mongo(self, *args: Any, **kwargs: Any):
        ...


class Document(BaseDocument, metaclass=TopLevelDocumentMetaclass):
    my_metaclass: Any = ...

    @property
    def pk(self):
        ...

    @pk.setter
    def pk(self, value: Any):
        ...

    def __hash__(self) -> Any:
        ...

    def to_mongo(self, *args: Any, **kwargs: Any):
        ...

    def modify(self, query: Optional[Any] = ..., **update: Any):
        ...

    def save(
        self,
        force_insert: bool = ...,
        validate: bool = ...,
        clean: bool = ...,
        write_concern: Optional[Any] = ...,
        cascade: Optional[Any] = ...,
        cascade_kwargs: Optional[Any] = ...,
        _refs: Optional[Any] = ...,
        save_condition: Optional[Any] = ...,
        signal_kwargs: Optional[Any] = ...,
        **kwargs: Any
    ):
        ...

    def cascade_save(self, **kwargs: Any) -> None:
        ...

    def update(self, **kwargs: Any):
        ...

    def delete(self, signal_kwargs: Optional[Any] = ..., **write_concern: Any) -> None:
        ...

    def switch_db(self, db_alias: Any, keep_created: bool = ...):
        ...

    def switch_collection(self, collection_name: Any, keep_created: bool = ...):
        ...

    def select_related(self, max_depth: int = ...):
        ...

    def reload(self, *fields: Any, **kwargs: Any):
        ...

    def to_dbref(self):
        ...

    @classmethod
    def register_delete_rule(cls, document_cls: Any, field_name: Any, rule: Any) -> None:
        ...

    @classmethod
    def drop_collection(cls) -> None:
        ...

    @classmethod
    def create_index(cls, keys: Any, background: bool = ..., **kwargs: Any):
        ...

    @classmethod
    def ensure_index(cls, key_or_list: Any, background: bool = ..., **kwargs: Any):
        ...

    @classmethod
    def ensure_indexes(cls) -> None:
        ...

    @classmethod
    def list_indexes(cls):
        ...

    @classmethod
    def compare_indexes(cls):
        ...

    @classmethod
    def objects(cls, *args: Any, **kwargs: Any):
        ...


class DynamicDocument(Document, metaclass=TopLevelDocumentMetaclass):
    my_metaclass: Any = ...

    def __delattr__(self, *args: Any, **kwargs: Any) -> None:
        ...


class DynamicEmbeddedDocument(EmbeddedDocument, metaclass=DocumentMetaclass):
    my_metaclass: Any = ...

    def __delattr__(self, *args: Any, **kwargs: Any) -> None:
        ...


class MapReduceDocument:
    key: Any = ...
    value: Any = ...

    def __init__(self, document: Any, collection: Any, key: Any, value: Any) -> None:
        ...

    @property
    def object(self):
        ...
