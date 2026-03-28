from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from strawberry.django.views import GraphQLView
from apps.api.schema_combined import schema
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.http import JsonResponse


class JWTGraphQLView(GraphQLView):
    """GraphQL view that authenticates via JWT Bearer token."""
    def get_context(self, request, response):
        context = super().get_context(request, response)
        # Try JWT auth
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Bearer "):
            try:
                jwt_auth = JWTAuthentication()
                validated = jwt_auth.authenticate(request)
                if validated:
                    request.user = validated[0]
            except Exception:
                pass
        return context


def auth_me(request):
    """Simple auth/me endpoint for React AuthContext (works without GraphQL client)."""
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Not authenticated"}, status=401)
    user = request.user
    return JsonResponse({
        "id": str(user.id),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_superuser": user.is_superuser,
    })


urlpatterns = [
    path("", csrf_exempt(JWTGraphQLView.as_view(schema=schema)), name="graphql"),
    path("auth/me/", auth_me, name="auth-me"),
]
