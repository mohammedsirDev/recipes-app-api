# This file is the WAITER of your API.
# The waiter takes your order (request) and brings you food (response).

from rest_framework import generics, authentication, permissions
# "generics" is like a menu of pre-built views Django already made for you.
# Instead of building everything from scratch,
# you just pick what you need from the menu.
from user.serializers import UserSerializer, AuthTokenSerializer
# Remember the serializer we made earlier?
# The translator between JSON and Python?
# We're bringing it in here so the view can use it.

from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.settings import api_settings

# CreateAPIView is a pre-built view that ONLY does one thing:
# CREATE something (in our case, a new user)
#
# Think of it like buying a pre-built PC vs building one yourself.
# generics.CreateAPIView already has everything wired up:
# ✅ accepts POST requests
# ✅ validates the data
# ✅ saves to the database
# ✅ returns a response
# You don't write any of that — it's already done for you!


class CreateUserView(generics.CreateAPIView):

    # This one line is ALL you need to tell Django:
    # "Hey, when someone sends data to this view,
    #  use UserSerializer to validate and save it"
    #
    # That's it. One line.
    # Django figures out the rest automatically.
    serializer_class = UserSerializer


class CreateTokenView(ObtainAuthToken):
    """Create a new auth token for user."""
    serializer_class = AuthTokenSerializer
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES


class ManagerUserView(generics.RetrieveUpdateAPIView):
    """Manage the authenticated user."""
    serializer_class = UserSerializer
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """Retrieve and return the authenticated user."""
        return self.request.user
