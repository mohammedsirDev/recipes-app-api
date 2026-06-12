# This file tests our "create user" API endpoint.
# Think of tests like a robot that checks your work automatically.
# Every time you change code, you run tests to make sure nothing broke.

# gives us tools to write tests
from django.test import TestCase
# gets our User model (the thing that stores users)
from django.contrib.auth import get_user_model
# turns a url name like 'user:create' into an actual url like
# '/api/user/create/'
from django.urls import reverse

# a fake browser we use to make requests in tests
from rest_framework.test import APIClient
# a list of http status codes like 200, 201, 400 etc.
from rest_framework import status


# Instead of typing '/api/user/create/' everywhere, we save it in a variable.
# reverse() figures out the actual URL from the name we gave it in urls.py
CREATE_USER_URL = reverse('user:create')
TOKEN_URL = reverse('user:token')
ME_URL = reverse('user:me')

# This is a helper function — we'll use it to quickly create a user in tests
# **params means "accept any keyword arguments" like email=, password=, name=


def create_user(**params):
    """Create and return a new user."""
    return get_user_model().objects.create_user(**params)


# A "Test Class" is just a group of related tests.
# "Public" means these are tests for endpoints that DON'T require login.
class PublicUserApiTests(TestCase):

    # setUp() runs automatically BEFORE every single test.
    # Here we create a fake browser (APIClient) so we can send fake requests.
    def setUp(self):
        self.client = APIClient()

    # ----------------------------------------------------------------
    # TEST 1: Can we create a user successfully?
    # ----------------------------------------------------------------
    def test_create_user_success(self):

        # This is the data we'll send to the API — like filling out a sign up
        # form
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Test Name',
        }

        # Send a POST request to the create user URL with our data
        # This is like clicking "Submit" on a sign up form
        res = self.client.post(CREATE_USER_URL, payload)

        # Check that the server replied with 201 (which means "Created successfully")
        # If we get anything else, the test fails
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # Now go find that user in the database using the email we sent
        user = get_user_model().objects.get(email=payload['email'])

        # Check that the password was saved correctly
        # We use check_password() because passwords are stored encrypted —
        # we can't just compare them directly
        self.assertTrue(user.check_password(payload['password']))

        # Make sure the API response does NOT include the password
        # We never want to send passwords back — that's a security risk!
        self.assertNotIn('password', res.data)

    # ----------------------------------------------------------------
    # TEST 2: What if someone tries to sign up with an email already in use?
    # ----------------------------------------------------------------
    def test_user_with_email_exists_error(self):

        payload = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Test Name',
        }

        # First, we CREATE a user with this email directly in the database
        create_user(**payload)

        # Now we try to sign up AGAIN with the same email via the API
        res = self.client.post(CREATE_USER_URL, payload)

        # The server should say 400 (which means "Bad Request" / something went wrong)
        # Because you can't have two accounts with the same email
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # ----------------------------------------------------------------
    # TEST 3: What if the password is too short?
    # ----------------------------------------------------------------
    def test_password_too_short_error(self):

        payload = {
            'email': 'test@example.com',
            'password': 'pw',        # only 2 characters — too short!
            'name': 'Test name',
        }

        # Try to create a user with a weak password
        res = self.client.post(CREATE_USER_URL, payload)

        # Server should reject it with 400 (Bad Request)
        # ⚠️ BUG FIX: was HTTP_400_REQUEST — the correct name is HTTP_400_BAD_REQUEST
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # Now double-check that the user was NOT actually saved in the database.
        # .filter() searches for users with that email, .exists() returns True/False
        user_exists = get_user_model().objects.filter(
            email=payload['email']
        ).exists()

        # We want this to be FALSE — the user should NOT exist because password
        # was too short
        self.assertFalse(user_exists)

    # -------------------------------------------------------
    # TEST 1: Does the API give us a token when we login correctly?
    # -------------------------------------------------------

    def test_create_token_for_user(self):

        # First we create a user in the database
        # Think of it like registering an account before trying to login
        user_details = {
            'name': 'Test Name',
            'email': 'test@example.com',
            'password': 'test-user-password123',
        }
        create_user(**user_details)

        # This is what we send to the login endpoint
        # Just email and password — like typing into a login form
        payload = {
            'email': user_details['email'],
            'password': user_details['password'],
        }

        # We send the login request to the API
        # Like clicking the "Login" button
        res = self.client.post(TOKEN_URL, payload)

        # Check that the response contains a token
        # A token is like a KEY 🔑 the server gives you after login
        # You use this key for every request after that instead of sending
        # password every time
        self.assertIn('token', res.data)

        # Check the status code is 200 which means "everything went fine"
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    # -------------------------------------------------------
    # TEST 2: What if someone types the WRONG password?
    # -------------------------------------------------------

    def test_create_token_bad_credentials(self):

        # Create a user with the CORRECT password "goodpass"
        create_user(email='test@example.com', password='goodpass')

        # But now try to login with the WRONG password "badpass"
        # Like trying to open a door with the wrong key 🔑❌
        payload = {'email': 'test@example.com', 'password': 'badpass'}
        res = self.client.post(TOKEN_URL, payload)

        # Make sure NO token was returned
        # Wrong password = no key for you!
        self.assertNotIn('token', res.data)

        # Server should reply with 400 which means "you did something wrong"
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # -------------------------------------------------------
    # TEST 3: What if someone sends a BLANK password?
    # -------------------------------------------------------

    def test_create_token_blank_password(self):

        # Try to login with an empty password
        # Like knocking on a door and saying your password is literally nothing
        # 😂
        payload = {'email': 'test@example.com', 'password': ''}
        res = self.client.post(TOKEN_URL, payload)

        # No token — blank password is not allowed!
        self.assertNotIn('token', res.data)

        # Server should reply with 400 — "seriously? blank password?"
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrive_user_unauthorized(self):
        """Test authentication is required for users."""
        res = self.client.get(ME_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserApiTests(TestCase):
    """Test API requests that require authentication."""

    def setUp(self):
        # Create a fake user in the database before each test
        self.user = create_user(
            email='test@example.com',
            password='testpass123',
            name='Test Name'
        )
        # Create a fake browser that can send requests
        self.client = APIClient()
        # Skip login — just tell the client "you ARE this user"
        self.client.force_authenticate(user=self.user)

    def test_retrieve_profile_success(self):
        """Test retrieving profile for logged in user."""
        # Logged-in user hits the /me/ endpoint
        res = self.client.get(ME_URL)

        # Make sure server replied with 200 = all good
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Make sure the returned data matches the user's name and email
        # (no password should ever be returned)
        self.assertEqual(res.data, {
            'name': self.user.name,
            'email': self.user.email,
        })

    def test_post_me_not_allowed(self):
        """Test POST is not allowed for the ME endpoint."""
        # Try to POST empty data to /me/ — this should be rejected
        res = self.client.post(ME_URL, {})

        # Expect 405 = "you can't do that here"
        # BUG: HTTTP_405_method_not_allowed is wrong — fix to
        # HTTP_405_METHOD_NOT_ALLOWED
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_user_profile(self):
        """Test updating the user profile for the authenticated user."""
        # New data we want to send to the server
        payload = {'name': 'Updated name', 'password': 'newpassword123'}

        # PATCH = only update what we send, don't touch the rest
        res = self.client.patch(ME_URL, payload)

        # Refresh self.user from the database — the in-memory version is stale
        self.user.refresh_from_db()

        # Check the name was actually updated in the database
        self.assertEqual(self.user.name, payload['name'])

        # check_password() checks the hashed version — never compare raw
        # passwords
        self.assertTrue(self.user.check_password(payload['password']))

        # Make sure the server replied with 200 = all good
        # BUG: Htpp_200_ok is wrong — fix to HTTP_200_OK
        self.assertEqual(res.status_code, status.HTTP_200_OK)
