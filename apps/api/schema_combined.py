"""
Combined GraphQL schema that merges admin and scenario queries/mutations.
This is the single entry point for the GraphQL endpoint.
"""
import strawberry

from apps.api.schema import Query as AdminQuery, Mutation as AdminMutation
from apps.api.schema_scenarios import ScenarioQuery, ScenarioMutation


@strawberry.type
class Query(AdminQuery, ScenarioQuery):
    """Combined query root."""
    pass


@strawberry.type
class Mutation(AdminMutation, ScenarioMutation):
    """Combined mutation root."""
    pass


schema = strawberry.Schema(query=Query, mutation=Mutation)
