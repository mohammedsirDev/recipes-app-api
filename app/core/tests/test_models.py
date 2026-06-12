"""
Tests for models
"""

# We need these two tools from Django:
# - TestCase: gives us the ability to write and run tests
# - get_user_model: gives us access to the User model
#  (the thing that stores users in the database)
from django.test import TestCase
from django.contrib.auth import get_user_model

from unittest.mock import patch
from decimal import Decimal
from core import models

# A "TestCase class" is just a container that holds all our tests
# Think of it like a folder named "Model Tests"


def create_user(email='user@example.com', password='testpass123'):
    """Create and return a new user."""
    return get_user_model().objects.create_user(email, password)


class ModelTest(TestCase):
    """Test models."""

    # This is ONE test inside that folder
    # The name starts with "test_" so Django knows to run it automatically
    def test_create_user_with_email_successful(self):
        """Test creating a user with an email is successful."""

        # ----------------------------------------------------------------
        # STEP 1: Prepare fake user data to test with
        # ----------------------------------------------------------------
        email = 'test@example.com'   # ✅ fixed version
        # The password we want to test with
        # (just a normal string, no bug here)
        password = 'testpass123'

        # ----------------------------------------------------------------
        # STEP 2: Create the user in the database
        # ----------------------------------------------------------------

        # get_user_model() → fetches whatever User model this project uses
        # .objects.create_user() → creates a new user and saves
        #  it to the database
        # We pass in the email and password we prepared above
        # Django will automatically HASH (scramble) the password before saving
        # So the real password is NEVER stored — only a scrambled version
        user = get_user_model().objects.create_user(
            email=email,
            password=password,
        )

        # ----------------------------------------------------------------
        # STEP 3: Check everything saved correctly
        # ----------------------------------------------------------------

        # CHECK 1: Did the email save correctly?
        # self.assertEqual(a, b) means "check that a and b are the same"
        # If they are NOT the same → test FAILS ❌
        # If they ARE the same    → test PASSES ✅
        self.assertEqual(user.email, email)

        # CHECK 2: Does the password work?
        # Remember: Django saved a scrambled version of the password
        # check_password() takes the plain password we give it,
        # scrambles it the same way, and compares it to what's stored
        # If they match returns True test PASSES
        # If they don't returns False test FAILS
        self.assertTrue(user.check_password(password))

    def test_new_user_email_normalized(self):
        """Test email is normalized for new users."""

        # list of (what you type in,  what should be saved)
        sample_emails = [
            ['test1@EXAMPLE.COM', 'test1@example.com'],
            ['Test2@Example.com', 'Test2@example.com'],
            ['TEST3@EXAMPLE.COM', 'TEST3@example.com'],
            ['test4@example.COM', 'test4@example.com'],
        ]

        for email, expected in sample_emails:

            # create a user with the raw un-normalized email
            user = get_user_model().objects.create_user(email, 'sample123')

            # check Django saved it normalized
            self.assertEqual(user.email, expected)

    def test_new_user_without_email_raises_error(self):
        """Test that creating a user without an email raises a ValueError"""
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user('', 'test123')

    def test_create_superuser(self):
        """Test creating a superuser."""
        user = get_user_model().objects.create_superuser(
            'test@example.com',
            'test123'
        )

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_create_recipe(self):
        """Test creating a recipe is successful."""

        # Create a fake user first — every recipe needs an owner
        user = get_user_model().objects.create_user(
            'test@example.com',
            'testpass123',
        )

        # Create a fake recipe in the database owned by the user above
        recipe = models.Recipe.objects.create(
            # The owner of this recipe
            user=user,
            # The name of the recipe
            title='Sample recipe name',
            # How long it takes to cook in minutes
            time_minutes=5,
            # Use Decimal for money — normal floats are inaccurate e.g 5.50 =
            # 5.4999999
            price=Decimal('5.50'),
            # A short description of the recipe
            description='Sample recipe description.',
        )

        # Check that printing the recipe shows its title
        # e.g str(recipe) should return 'Sample recipe name'
        # not something ugly like 'Recipe object (1)'
        self.assertEqual(str(recipe), recipe.title)

    def test_create_tag(self):
        """Test creating a tag is successful."""

        user = create_user()
        tag = models.Tag.objects.create(user=user, name='Tag1')

        self.assertEqual(str(tag), tag.name)

    def test_create_ingredient(self):
        """Test creating an ingredient is successful."""
        user = create_user()
        ingredient = models.Ingredient.objects.create(
            user=user,
            name='Ingredient1',
        )

        self.assertEqual(str(ingredient), ingredient.name)

    @patch('core.models.uuid.uuid4')
    def test_recipe_file_name_uuid(self, mock_uuid):
        """Test generating image path."""
        uuid = 'Test-uuid'
        mock_uuid.return_value = uuid
        file_path = models.recipe_image_file_path(None, 'example.jpg')

        self.assertEqual(file_path, f'uploads/recipe/{uuid}.jpg')
