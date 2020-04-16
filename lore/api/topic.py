import logging

from flask import Blueprint, current_app
from flask_graphql import GraphQLView
from lore.extensions import csrf
from lore.model.gql_schema_topics import schema

logger = current_app.logger if current_app else logging.getLogger(__name__)

topic_app = Blueprint('topic', __name__)

topic_app.add_url_rule(
    '/graphql',
    view_func=GraphQLView.as_view('graphql', schema=schema, graphiql=True)
)

csrf.exempt(topic_app)
