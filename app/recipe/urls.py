"""
URL mappings for the recipe app.
"""

from django.urls import (
    path,    # Used to define individual URL patterns
    # Used to include an external set of URLs (e.g. router-generated ones)
    include,
)

from rest_framework.routers import DefaultRouter
# DefaultRouter auto-generates standard RESTful URL patterns for a ViewSet:
#   GET/POST   /recipes/        -> list & create
#   GET/PUT/PATCH/DELETE /recipes/<id>/  -> retrieve, update & delete
# It also provides a browsable API root at '/'

from recipe import views  # Import views to register with the router


router = DefaultRouter()
# Create a router instance that will auto-build URL patterns for
# registered viewsets

router.register('recipes', views.RecipeViewSet)
router.register('tags', views.TagViewSet)
router.register('ingredients', views.IngredientViewSet)
# Registers RecipeViewSet under the 'recipes' prefix, generating:
#   /recipes/       -> RecipeViewSet.list()  & .create()
#   /recipes/<id>/  -> RecipeViewSet.retrieve(), .update(), .partial_update(), .destroy()


app_name = 'recipe'
# Sets the application namespace for URL reversing.
# Allows referencing URLs like: reverse('recipe:recipe-list')
# Avoids name collisions when multiple apps share similar URL names.


urlpatterns = [
    path('', include(router.urls))
    # Mount all router-generated URLs at the root of this app's URL space.
    # Since this file is included in the project's main urls.py under 'api/recipe/',
    # the full URL paths become:
    #   api/recipe/recipes/
    #   api/recipe/recipes/<id>/
]
