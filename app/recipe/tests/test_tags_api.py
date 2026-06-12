"""
Tests for the tags API
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Tag, Recipe
from recipe.serializers import TagSerializer

# The URL for the tags endpoint
# reverse() means if the URL changes our tests still work
TAGS_URL = reverse('recipe:tag-list')


def detail_url(tag_id):
    """Create and return a tag detail url."""
    return reverse('recipe:tag-detail', args=[tag_id])

# Helper function to create a user quickly
# Instead of writing get_user_model().objects.create_user() every time
# we just call create_user()


def create_user(email='user@example.com', password='testpass123'):
    """Create and return a user."""
    return get_user_model().objects.create_user(email=email, password=password)


# ============================================================
# PART 1: Test what happens when nobody is logged in
# Like a stranger trying to enter a restaurant 🍽️
# ============================================================
class PublicTagsApiTests(TestCase):
    """Test unauthenticated API requests."""

    # This runs before every test automatically
    # We create a test client with NO user logged in
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required for retrieving tags."""

        # Try to get tags WITHOUT being logged in
        res = self.client.get(TAGS_URL)

        # We should get 401 UNAUTHORIZED
        # = "You are not logged in, go away!" 🚫
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


# ============================================================
# PART 2: Test what happens when someone IS logged in
# Like a real customer sitting at their table 🪑
# ============================================================
class PrivateTagsApiTests(TestCase):
    """Test authenticated API requests."""

    # This runs before every test automatically
    # We create a user and log them in
    def setUp(self):
        # Create a user
        self.user = create_user()

        # Create a test client
        self.client = APIClient()

        # Force login the user
        # Skip the token process, just log them in directly for testing
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        """Test retrieving a list of tags."""

        # Create 2 tags in the database before the test
        # Like writing 2 sticky notes 📝
        Tag.objects.create(user=self.user, name='Vegan')
        Tag.objects.create(user=self.user, name='Dessert')

        # Send GET request to get all tags
        res = self.client.get(TAGS_URL)

        # Get the same tags from the database ourselves
        # So we can compare with what the API returned
        # order_by('-name') = alphabetically reversed order (Z to A)
        tags = Tag.objects.all().order_by('-name')

        # Convert the tags to JSON using the serializer
        # many=True = there are MULTIPLE tags not just one
        serializer = TagSerializer(tags, many=True)

        # ✅ Check the request worked
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # ✅ Check the data returned matches what is in the database
        self.assertEqual(res.data, serializer.data)

    def test_tags_limited_to_user(self):
        """Test list of tags is limited to authenticated user."""

        # Create a second user with their own tag
        # This tag should NOT appear in our results
        user2 = create_user(email='user2@example.com')
        Tag.objects.create(user=user2, name='Fruity')

        # Create OUR tag — this is the only one we should see
        tag = Tag.objects.create(user=self.user, name='Comfort food')

        # Send GET request as self.user (the logged in user)
        res = self.client.get(TAGS_URL)

        # ✅ Check the request worked
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # ✅ Check we only got 1 tag back
        # Even though there are 2 tags in the database
        # We should only see OUR tag not user2's tag
        self.assertEqual(len(res.data), 1)

        # ✅ Check the tag we got is specifically OUR tag
        self.assertEqual(res.data[0]['name'], tag.name)
        self.assertEqual(res.data[0]['id'], tag.id)

    def test_update_tag(self):
        """Test updating a tag."""

        tag = Tag.objects.create(user=self.user, name='After Dinner')
        # Create a real tag in the database with name 'After Dinner'
        # This is the tag we're going to update.
        # Think of it like creating a label sticker 🏷️ that says 'After Dinner'

        payload = {'name': 'Dessert'}
        # This is what we want to change the tag name TO.
        # We're saying "rename this tag from 'After Dinner' to 'Dessert'"

        url = detail_url(tag.id)
        # Build the URL for this specific tag
        # e.g. /api/recipe/tags/1/

        res = self.client.patch(url, payload)
        # Send a PATCH request — like saying:
        # "Hey API, just update the name, leave everything else alone!" 🩹

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # 200 = "Updated successfully!" ✅
        # If we get anything else the test fails immediately.

        tag.refresh_from_db()
        # Reload the tag from the database to get the latest values.
        # Without this, tag.name still says 'After Dinner' in memory
        # even if the database already changed it. 🔄

        self.assertEqual(tag.name, payload['name'])
        # "Did the name actually change to 'Dessert'?"
        #   database name = 'Dessert' ✅
        #   payload name  = 'Dessert' ✅
        # If they match — tag was updated correctly! 😄

    def test_delete_tag(self):
        """Test deleting a tag."""
        tag = Tag.objects.create(user=self.user, name='Breakfast')

        url = detail_url(tag.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        tags = Tag.objects.filter(user=self.user)
        self.assertFalse(tags.exists())

    def test_filter_tags_assigned_to_recipes(self):
        """Test listing tags to those assigned to recipes."""
        tag1 = Tag.objects.create(user=self.user, name='Breakfast')
        tag2 = Tag.objects.create(user=self.user, name='Lunch')
        recipe = Recipe.objects.create(
            title='Green Eggs on Toast',
            time_minutes=10,
            price=Decimal('2.50'),
            user=self.user,

        )
        recipe.tags.add(tag1)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        s1 = TagSerializer(tag1)
        s2 = TagSerializer(tag2)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filterd_tags_unique(self):
        """Test filterd tags return a unique list."""
        tag = Tag.objects.create(user=self.user, name='Beakfast')
        Tag.objects.create(user=self.user, name='Dinner')
        recipe1 = Recipe.objects.create(
            title='Pancakes',
            time_minutes=5,
            price=Decimal('5.00'),
            user=self.user
        )
        recipe2 = Recipe.objects.create(
            title='Porridge',
            time_minutes=3,
            price=Decimal('2.00'),
            user=self.user,
        )
        recipe1.tags.add(tag)
        recipe2.tags.add(tag)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
