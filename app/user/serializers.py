# ============================================================
# A "Serializer" is like a TRANSLATOR between Python and JSON.
#
# When someone sends data TO your API (like a sign up form):
#   JSON data --> Serializer --> Python object (User)
#
# When your API sends data back to someone:
#   Python object (User) --> Serializer --> JSON data
#
# Think of it like an ATM machine:
#   You put in your card (JSON) --> ATM processes it --> gives you money (Python object)
#   or the other way around
# ============================================================


# get_user_model  → gives us the User table from the database
# authenticate    → Django's built in login checker (checks email + password)
from django.contrib.auth import get_user_model, authenticate

# gives us all the Serializer tools we need
from rest_framework import serializers

# _ means "translate this text" so it works in different languages
# (Arabic, French, etc)
from django.utils.translation import gettext as _


# ============================================================
# PART 1: UserSerializer
# This is used for REGISTERING a new user
# When someone fills out the sign up form, this handles it
# ============================================================

# ModelSerializer means:
# "Look at my User model in the database and build the serializer from it"
# Instead of writing all fields manually, it reads the model and does it
# for you
class UserSerializer(serializers.ModelSerializer):

    # Meta is like the SETTINGS section of this serializer
    # It tells Django:
    #   - which model to use
    #   - which fields to allow
    #   - any special rules
    class Meta:

        # "Which database table are we working with?"
        # get_user_model() returns our custom User model
        # We use get_user_model() instead of importing User directly
        # because it always returns the correct User model even if we
        # customized it
        model = get_user_model()

        # "Which fields do we allow the user to send?"
        # Our User model might have 20 fields but we only allow these 3
        # Any other fields the user sends will be completely IGNORED
        # Think of it like a form with only 3 boxes to fill in
        fields = ['email', 'password', 'name']

        # "Special rules for specific fields"
        # Here we add extra rules on top of the basic field rules
        extra_kwargs = {
            'password': {
                # write_only = True means:
                # ✅ User CAN send us their password (writing)
                # ❌ We will NEVER send the password back in any response (reading)
                #
                # Just like an ATM:
                # You type your PIN in ✅
                # The ATM never shows your PIN on the screen ❌
                'write_only': True,

                # Password must be at least 5 characters long
                # ✅ "hello123" is accepted
                # ❌ "hi" is rejected
                'min_length': 5,
            }
        }

    # This method runs automatically when we call .save() on the serializer
    # "validated_data" is the clean data that already passed all the rules above
    # at this point we know:
    #   - email is a valid email ✅
    #   - password is at least 5 characters ✅
    #   - name is provided ✅
    def create(self, validated_data):

        # We do NOT use User.objects.create() here!
        # Because create() saves the password as PLAIN TEXT which is very dangerous:
        # ❌ password = "mypassword123"  (anyone who hacks the database can read it)
        #
        # Instead we use create_user() which ENCRYPTS the password before saving:
        # ✅ password = "$2b$12$KIXqQ8..."  (even if hacked, nobody can read it)
        #
        # **validated_data means "pass all the fields at once" which is the same as:
        # create_user(email=..., password=..., name=...)
        # but shorter and cleaner
        return get_user_model().objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        """Update and retrun user."""
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)

        if password:
            user.set_password(password)
            user.save()
        return user
# ============================================================
# PART 2: AuthTokenSerializer
# This is used for LOGGING IN an existing user
# When someone fills out the login form, this handles it
# It checks their credentials and if correct, hands them a TOKEN
# ============================================================

# Regular Serializer (not ModelSerializer) because we are not
# creating or reading from the database directly here
# We are just validating credentials and checking if user exists


class AuthTokenSerializer(serializers.Serializer):
    """Serializer for the user auth token."""

    # Expect an email from the user
    # EmailField automatically checks if it looks like a real email
    # ✅ "john@example.com"  accepted
    # ❌ "notanemail"        rejected
    # ❌ "missing@"         rejected
    email = serializers.EmailField()

    # Expect a password from the user
    password = serializers.CharField(
        # Makes the password show as **** in the browsable API
        # So nobody looking at the screen can see the password
        style={'input_type': 'password'},

        # Do NOT remove spaces from the password
        # If someone's password is " mypass " the spaces are kept exactly as is
        # Because spaces might be part of their password intentionally
        trim_whitespace=False,
    )

    # This method runs automatically after the fields above are checked
    # "attrs" is a dictionary of the data the user sent:
    # attrs = {
    #     'email': 'john@example.com',
    #     'password': 'mypassword123'
    # }
    def validate(self, attrs):
        """Validate and authenticate the user."""

        # Pull out the email from the dictionary into its own variable
        # Makes the code cleaner and easier to read below
        email = attrs.get('email')

        # Pull out the password from the dictionary into its own variable
        password = attrs.get('password')

        # authenticate() is Django's built in LOGIN CHECKER
        # Think of it like a BOUNCER at a club:
        # It goes to the database and checks:
        #   - Does a user with this email exist?
        #   - Does the password match?
        #
        # username=email
        #   → Django expects "username" but we use email as our username
        #   → So we pass the email as the username
        #
        # password=password
        #   → The password the user typed in
        #
        # request=self.context.get('request')
        #   → Pass the full HTTP request (IP address, browser, location, etc)
        #   → Useful for extra security checks like:
        #       - Block IP after 5 failed attempts
        #       - Flag logins from suspicious locations
        #       - Detect unusual activity
        #   → self.context is a backpack the serializer carries with extra info
        #   → .get('request') safely takes the request out of that backpack
        #   → If the backpack is empty it returns None instead of crashing
        #
        # Returns:
        #   ✅ User object → if email and password are correct
        #   ❌ None        → if anything is wrong
        user = authenticate(
            request=self.context.get('request'),
            username=email,
            password=password,
        )

        # If authenticate() returned None, meaning wrong email or password
        if not user:
            # Create an error message
            # _() wraps it for translation support (Arabic, French, etc)
            msg = _('Unable to authenticate with provided credentials')

            # Throw an error and STOP everything
            # The user gets back a 400 Bad Request response with the error message
            # code='authorization' helps developers identify what TYPE of error
            # it is
            raise serializers.ValidationError(msg, code='authorization')

        # If we made it here, login SUCCEEDED! ✅
        # Add the verified user object to attrs
        # So the view can grab it later with:
        # user = serializer.validated_data['user']
        attrs['user'] = user

        # Return the attrs dictionary which now contains:
        # {
        #     'email': 'john@example.com',
        #     'password': 'mypassword123',
        #     'user': <User object>       ← the verified user
        # }
        return attrs
