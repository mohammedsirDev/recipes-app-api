"""
Views for the recipe API.
"""

from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiParameter,
    OpenApiTypes,
)


from rest_framework import status, viewsets, mixins
# viewsets.ModelViewSet provides full CRUD operations:
# list, create, retrieve, update, partial_update, destroy — all auto-handled

from rest_framework.authentication import TokenAuthentication
# TokenAuthentication: validates requests using a token in the Authorization header
# e.g. Authorization: Token <your_token_here>

from rest_framework.permissions import IsAuthenticated
# IsAuthenticated: blocks any unauthenticated request from accessing this view

# The Recipe model to query against
from core.models import Recipe, Tag, Ingredient
from recipe import serializers          # Our custom serializers for Recipe data

from rest_framework.decorators import action
from rest_framework.response import Response


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                'tags',
                OpenApiTypes.STR,
                description='Comma separated list of IDs to filter',
            ),
            OpenApiParameter(
                'ingredients',
                OpenApiTypes.STR,
                description='Comma separated list of ingredient IDs to filter',
            )
        ]
    )
)
class RecipeViewSet(viewsets.ModelViewSet):
    """
    View for managing recipe APIs.
    Provides full CRUD endpoints automatically:
      GET    /recipes/       -> list all recipes
      POST   /recipes/       -> create a new recipe
      GET    /recipes/<id>/  -> retrieve a single recipe
      PUT    /recipes/<id>/  -> fully update a recipe
      PATCH  /recipes/<id>/  -> partially update a recipe
      DELETE /recipes/<id>/  -> delete a recipe
    """

    serializer_class = serializers.RecipeDetailsSerializer
    # Defines which serializer handles input validation and output formatting

    queryset = Recipe.objects.all()
    # Base queryset — fetches all recipes from the DB.
    # This gets further filtered in get_queryset() to scope it per user.

    authentication_classes = [TokenAuthentication]
    # Only token-authenticated requests are accepted.
    # DRF checks the Authorization header for a valid token before proceeding.

    permission_classes = [IsAuthenticated]
    # Even after authentication, the user must be active/authenticated.
    # Unauthenticated users receive a 401 Unauthorized response.

    def _params_to_ints(self, qs):
        """Convert a list of strings to integers."""
        return [int(str_id) for str_id in qs.split(',')]

    def get_queryset(self):
        tags = self.request.query_params.get('tags')
        ingredients = self.request.query_params.get('ingredients')
        queryset = self.queryset

        if tags:
            tag_ids = self._params_to_ints(tags)
            queryset = queryset.filter(tags__id__in=tag_ids)

        if ingredients:
            ingredient_ids = self._params_to_ints(ingredients)
            queryset = queryset.filter(ingredients__id__in=ingredient_ids)

        return queryset.filter(
            user=self.request.user
        ).order_by('-id').distinct()

        """
        Retrieve recipes belonging to the authenticated user only.
        Overrides the default queryset to prevent users from
        accessing each other's recipes (data isolation).
        Results are ordered by '-id' (newest first).
        """
        return self.queryset.filter(user=self.request.user).order_by('-id')
        # self.request.user -> the currently authenticated user from the token
        # .filter(user=...) -> scopes results to that user's recipes only
        # .order_by('-id')  -> '-' prefix means descending order (newest first)

    def get_serializer_class(self):
        """Return the serializer class for request."""
        # DRF automatically calls this method before every request
        # to determine which serializer should handle the data.
        # We override it to return different serializers for different actions.

        if self.action == 'list':
            # 'list' action = GET /recipes/ (fetching ALL recipes)
            # Use the lightweight serializer — no description needed
            # when displaying many recipes at once.
            return serializers.RecipeSerializer
        elif self.action == 'upload_image':
            return serializers.RecipeImageSerializer

        return self.serializer_class
        # Any other action falls back to the default serializer_class.
        # In our case that's RecipeDetailSerializer, which includes
        # all fields + description. This covers:
        #   retrieve      -> GET    /recipes/<id>/
        #   create        -> POST   /recipes/
        #   update        -> PUT    /recipes/<id>/
        #   partial_update-> PATCH  /recipes/<id>/
        #   destroy       -> DELETE /recipes/<id>/

    def perform_create(self, serializer):
        """Create a new recipe."""

        # serializer.save() → saves the recipe to the database
        # user=self.request.user → automatically attaches the logged in user to the recipe
        #
        # self         → this view
        # self.request → the HTTP request that came in (contains token, user, data etc)
        # self.request.user → the person who is currently logged in
        #
        # Why do we do this?
        # Because the user should NOT be sent in the request body
        # (that would be a security risk — anyone could fake a user id)
        # Instead we take it directly from the TOKEN
        # So we KNOW for sure who is creating the recipe
        #
        # Example:
        # ❌ Without this:
        #    recipe = Recipe(title="Pizza", user=???)  # who created this??
        #
        # ✅ With this:
        # recipe = Recipe(title="Pizza", user=john) # always the logged in user
        serializer.save(user=self.request.user)

    @action(methods=['POST'], detail=True, url_path='upload-image')
    def upload_image(self, request, pk=None):
        """Upload an image to recipe."""
        recipe = self.get_object()
        serializer = self.get_serializer(recipe, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                'assigned_only',
                OpenApiTypes.INT, enum=[0, 1],
                description='Filter by items assigned to recipes.'
            )
        ]
    )
)
class BaseRecipeAttrViewSet(mixins.DestroyModelMixin,
                            mixins.UpdateModelMixin,
                            mixins.ListModelMixin,
                            viewsets.GenericViewSet):
    """Base viewset for recipe attributes."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter queryset to authenticated user."""
        assigned_only = bool(
            int(self.request.query_params.get('assigned_only', 0))
        )
        queryset = self.queryset  # ← only line changed
        if assigned_only:
            queryset = queryset.filter(recipe__isnull=False)

        return queryset.filter(
            user=self.request.user).order_by('-name').distinct()


class TagViewSet(BaseRecipeAttrViewSet):
    """Manage tags in the database."""

    serializer_class = serializers.TagSerializer
    queryset = Tag.objects.all()


class IngredientViewSet(BaseRecipeAttrViewSet):
    """Manage ingredients in database."""
    serializer_class = serializers.IngredientSerializer
    queryset = Ingredient.objects.all()
