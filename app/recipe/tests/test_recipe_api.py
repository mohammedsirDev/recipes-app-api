"""
Tests for recipe APIs
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient
from PIL import Image
import tempfile
import os
from core.models import Recipe, Tag, Ingredient
from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailsSerializer,
)

# the URL for the recipes list endpoint → /api/recipes/
RECIPES_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    """Create and return a recipe detail URL."""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def image_upload_url(recipe_id):
    """Create and return an image upload URL."""
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def create_recipe(user, **params):
    """Create and return a sample recipe."""
    # default values so we don't repeat them in every test
    defaults = {
        'title': 'Sample recipe title',
        'time_minutes': 22,
        'price': Decimal('5.25'),
        'link': 'http://example.com/recipe.pdf'
    }
    # override defaults with any custom values passed in
    defaults.update(params)

    # create and save the recipe in the DB
    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


class PublicRecipeAPITests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        # client with no user logged in
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call API."""
        # hit the endpoint without logging in
        res = self.client.get(RECIPES_URL)

        # should return 401 because no auth provided
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.client = APIClient()

        # create a real user in the DB
        self.user = get_user_model().objects.create_user(
            'user@example.com',
            'testpass123',
        )

        # force login — skips password check, just sets the user
        self.client.force_authenticate(self.user)

    def test_retrive_recipes(self):
        """Test retrieving a list of recipes."""
        # create 2 recipes for the logged in user
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        # GET /api/recipes/
        res = self.client.get(RECIPES_URL)

        # fetch all recipes from DB ordered by newest first
        recipes = Recipe.objects.all().order_by('-id')

        # serialize them (convert DB objects → JSON format)
        serializer = RecipeSerializer(recipes, many=True)

        # check response is 200
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # check response data matches what's in the DB
        self.assertEqual(res.data, serializer.data)

    def test_recipe_list_limited_to_user(self):
        """Test list of recipes is limited to authenticated user."""

        # create a second user
        other_user = get_user_model().objects.create_user(
            'other@example.com',
            'password12',
        )

        # create a recipe for other_user (should NOT appear in response)
        create_recipe(user=other_user)

        # create a recipe for self.user (should appear in response)
        create_recipe(user=self.user)

        # GET /api/recipes/ — logged in as self.user
        res = self.client.get(RECIPES_URL)

        # filter only self.user's recipes from DB
        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)

        # check 200
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # check response only contains self.user's recipe, not other_user's
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        """Test get recipe details."""

        recipe = create_recipe(user=self.user)
        # Create a fake recipe in the test database owned by the logged-in test user.
        # This gives us something real to fetch from the API.

        url = detail_url(recipe.id)
        # Build the URL for that specific recipe using its ID.
        # e.g. /api/recipe/recipes/1/

        res = self.client.get(url)
        # Hit the URL with a GET request using the authenticated test client.
        # res holds whatever the API sends back (status code + data).

        serializer = RecipeDetailsSerializer(recipe)
        # Manually serialize the same recipe — this is our EXPECTED result.
        # We're saying "this is what the API SHOULD have returned."

        self.assertEqual(res.data, serializer.data)
        # Compare actual vs expected:
        #   res.data        -> what the API actually returned
        #   serializer.data -> what we expected it to return
        # If they match  ✅ test passes  — API returns correct recipe data
        # If they don't  ❌ test fails   — API is returning something wrong

    def test_create_recipe(self):
        """Test creating a recipe"""

        # data we want to send to the API (keys will be used to check recipe
        # attributes later)
        payload = {
            'title': 'Sample a recipe',
            'time_minutes': 30,
            'price': Decimal('5.99'),
        }

        # send POST request to the API with the payload
        res = self.client.post(RECIPES_URL, payload)

        # did the API return 201 (created)? if not, test fails here
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # fetch the recipe object from the database using the id the API
        # returned
        recipe = Recipe.objects.get(id=res.data['id'])

        # loop gives us each key and value from payload one by one:
        # k='title',        v='Sample a recipe'
        # k='time_minutes', v=30
        # k='price',        v=Decimal('5.99')
        for k, v in payload.items():

            # getattr(recipe, k) fetches the value of that attribute from the database
            # example: when k='title' → getattr(recipe, 'title') → returns 'Sample a recipe'
            # then we check it equals v (what we originally sent)
            self.assertEqual(getattr(recipe, k), v)

        # check the recipe was assigned to the logged-in user automatically
        # (we never sent user in the payload, the API should handle this itself)
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        """Test partial update of a recipe"""

        # save the original link so we can check later that it didn't change
        original_link = 'https://example.com/recipe.pdf'

        # create a recipe in the database with a title and a link
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe title',
            link=original_link,
        )

        # we only want to update the title, nothing else
        payload = {'title': 'New recipe title'}

        # get the URL for this specific recipe ex: /api/recipes/1/
        url = detail_url(recipe.id)

        # PATCH means update only what I send, leave everything else alone
        res = self.client.patch(url, payload)

        # did the API return 200 (ok)? if not, test fails here
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # recipe variable is still old data in memory, this fetches the latest
        # from the database
        recipe.refresh_from_db()

        # did the title change to the new one?
        self.assertEqual(recipe.title, payload['title'])

        # did the link stay the same? we didn't send it so it should NOT change
        self.assertEqual(recipe.link, original_link)

        # did the user stay the same? nobody should be able to change the owner
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        """Test full update of recipe."""
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe title',
            link='https://example.com/recipe.pdf',
            description='Sample recipe description',
        )

        payload = {
            'title': 'New recipe title',
            'link': 'https://example.com/new-recipe.pdf',
            'description': 'Sample recipe description',
            'time_minutes': 30,
            'price': Decimal('2.50'),
        }
        url = detail_url(recipe.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)

        self.assertEqual(recipe.user, self.user)

    def test_update_user_return_error(self):
        """Test changing the recipe user results in an error."""

        new_user = get_user_model().objects.create_user(
            email='user2@example.com',
            password='test123'
        )
        # Create a second user — this is the "bad actor" we're
        # trying to transfer the recipe ownership to. 🚫

        recipe = create_recipe(user=self.user)
        # Create a recipe owned by the original logged-in user (self.user)

        payload = {'user': new_user.id}
        # The "attack" payload — trying to change the recipe's
        # owner to the new user by sending their id.

        url = detail_url(recipe.id)
        # Build the URL for this specific recipe
        # e.g. /api/recipes/1/

        self.client.patch(url, payload)
        # Send the PATCH request trying to change the owner.
        # We don't check the status code here — we only care
        # that the owner did NOT actually change in the database.

        recipe.refresh_from_db()
        # Reload the recipe from the database to get fresh values.
        # Without this we'd still see the old values in memory. 🔄

        self.assertEqual(recipe.user, self.user)
        # "Is the recipe STILL owned by the original user?"
        # YES ✅ — API correctly blocked the ownership change.
        # NO  ❌ — Security bug! Anyone can steal anyone's recipe!

    def test_delete_recipe(self):
        """Test deleting a recipe successful."""

        recipe = create_recipe(user=self.user)
        # Create a fake recipe in the database.
        # This is the recipe we're about to delete. 🗑️

        url = detail_url(recipe.id)
        # Build the URL for this specific recipe
        # e.g. /api/recipes/1/

        res = self.client.delete(url)
        # Send a DELETE request — like clicking the delete button.
        # res holds the response status code.

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        # 204 = "Deleted! Nothing to send back."          ✅
        # 404 = "Recipe not found!"                       ❌
        # 403 = "You don't have permission to do this!"   ❌

        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())
        # "Does this recipe still exist in the database?"
        # .filter(id=recipe.id) → look for the recipe by id
        # .exists()             → returns True if found, False if not
        # assertFalse()         → we EXPECT False — it should be gone!
        # Like checking the trash after deleting — make sure it's empty. 🗑️✅

    def test_recipe_other_users_recipe_error(self):
        """Test trying to delete another users recipe gives error."""
        new_user = get_user_model().objects.create_user(
            email='user2@example.com', password='pass123')
        recipe = create_recipe(user=new_user)
        url = detail_url(recipe.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tags(self):
        """Test creating a recipe with new tags."""

        payload = {
            'title': 'Thai Prawn Curry',
            'time_minutes': 30,
            'price': Decimal('2.50'),
            'tags': [{'name': 'Thai'}, {'name': 'Dinner'}]
        }
        # The data we're sending to create a recipe WITH tags.
        # 'tags' is a list of dictionaries — we're creating
        # the recipe AND its tags all in ONE single request.
        # Like ordering a burger WITH toppings in one order. 🍔

        res = self.client.post(RECIPES_URL, payload, format='json')
        # Send a POST request to create the recipe.
        # format='json' is IMPORTANT here because we're sending
        # nested data (tags inside recipe) — must be JSON not
        # regular form data, otherwise tags won't be read correctly.

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        # 201 = "Created successfully!" ✅
        # Always check status code first before anything else.
        # If this fails, no point checking the rest.

        recipes = Recipe.objects.filter(user=self.user)
        # Fetch ALL recipes belonging to this user from the database.
        # We go directly to the database to double check —
        # not just trusting what the API told us.

        self.assertEqual(recipes.count(), 1)
        # "Did we create exactly ONE recipe?" ✅
        # Makes sure we didn't accidentally create duplicates.

        recipe = recipes[0]
        # Grab the first (and only) recipe from the results.
        # Like taking the first item out of a list. 😄

        self.assertEqual(recipe.tags.count(), 2)
        # "Does this recipe have exactly TWO tags?"
        # We sent 'Thai' and 'Dinner' so we expect 2.
        # If only 1 or 0 tags were saved — test fails. ❌

        for tag in payload['tags']:
            # Loop through each tag we sent in the payload:
            # Round 1: tag = {'name': 'Thai'}
            # Round 2: tag = {'name': 'Dinner'}

            exists = recipe.tags.filter(
                name=tag['name'],  # look for this tag name
                user=self.user,    # make sure it belongs to correct user
            ).exists()
            # "Does this EXACT tag exist in the database
            #  AND belong to the correct user?"
            # Like checking each topping is actually on your burger. 🍔

            self.assertTrue(exists)
            # "Yes it exists!" ✅
            # If ANY tag is missing in the database — test fails. ❌
            # Runs twice — once for 'Thai', once for 'Dinner'

            # TEST 1:
            # "When I update a recipe, can I add a BRAND NEW tag at the same time?"
            # Start with a plain recipe → send PATCH with new tag 'Lunch'
            # → check 'Lunch' tag was CREATED and LINKED to recipe ✨

    def test_create_tag_on_update(self):
        """Test creating tag when updating a recipe."""

        recipe = create_recipe(user=self.user)
        # Create a plain recipe with NO tags.
        # Like a plain burger with no toppings. 🍔

        payload = {'tags': [{'name': 'Lunch'}]}
        # We want to ADD a brand new tag 'Lunch' to this recipe.
        # 'Lunch' doesn't exist in database yet — brand new! ✨

        url = detail_url(recipe.id)
        # Get the URL for this specific recipe
        # e.g. /api/recipes/1/

        res = self.client.patch(url, payload, format='json')
        # Send PATCH request — "hey API, add this tag to my recipe!"
        # format='json' needed because tags is nested data.
        # PATCH = update only what I send, leave rest alone 🩹

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # 200 = "Updated successfully!" ✅

        new_tag = Tag.objects.get(user=self.user, name='Lunch')
        # Go to database and find the 'Lunch' tag we just created.

        self.assertIn(new_tag, recipe.tags.all())
        # "Is the new 'Lunch' tag linked to this recipe?" ✅
        # recipe.tags.all() = all tags linked to this recipe

        # ─────────────────────────────────────────────────────────

        # TEST 2:
        # "When I swap a tag for a different one, does the OLD tag
        #  get REMOVED and the NEW tag get ADDED?"
        # Start with recipe that has 'Breakfast' → send PATCH with 'Lunch'
        # → check 'Lunch' is added ✅ and 'Breakfast' is gone ❌

    def test_update_recipe_assign_tag(self):
        """Test assigning an existing tag when updating a recipe."""

        tag_breakfast = Tag.objects.create(user=self.user, name='Breakfast')
        # Create a 'Breakfast' tag in database.
        # This is the OLD tag we're going to REPLACE. 🔄

        recipe = create_recipe(user=self.user)
        # Create a plain recipe with no tags.

        recipe.tags.add(tag_breakfast)
        # Add 'Breakfast' tag to the recipe.
        # Recipe now has: [Breakfast] 🏷️

        tag_lunch = Tag.objects.create(user=self.user, name='Lunch')
        # Create a 'Lunch' tag in database.
        # This is the NEW tag we want to REPLACE Breakfast with. ✨

        payload = {'tags': [{'name': 'Lunch'}]}
        # "Replace ALL tags with just 'Lunch'"
        # We're NOT sending 'Breakfast' — so it should be removed!
        # Before update: recipe tags = [Breakfast]
        # After update:  recipe tags = [Lunch]

        url = detail_url(recipe.id)
        # Get the URL for this specific recipe
        # e.g. /api/recipes/1/

        res = self.client.patch(url, payload, format='json')
        # Send PATCH request to swap the tags.
        # format='json' needed because tags is nested data.

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # 200 = "Updated successfully!" ✅

        recipe.refresh_from_db()
        # Reload recipe from database to get latest values.
        # Without this recipe still shows OLD tags in memory! 🔄

        self.assertIn(tag_lunch, recipe.tags.all())
        # "Is 'Lunch' now linked to the recipe?" ✅
        # recipe should now have: [Lunch] 🏷️

        self.assertNotIn(tag_breakfast, recipe.tags.all())
        # "Is 'Breakfast' GONE from the recipe?" ✅
        # assertNotIn = "this should NOT be in the list"
        # If Breakfast is still there — test fails! ❌

    # ─────────────────────────────────────────────────────────

    # TEST 3:
    # "When I send empty tags [], does it REMOVE ALL tags from recipe?"
    # Start with recipe that has 'Dessert' tag → send PATCH with []
    # → check recipe has ZERO tags left 🗑️

    def test_clear_recipe_tags(self):
        """Test clearing a recipes tags."""

        tag = Tag.objects.create(user=self.user, name='Dessert')
        # Create a 'Dessert' tag in database.

        recipe = create_recipe(user=self.user)
        # Create a plain recipe with no tags.

        recipe.tags.add(tag)
        # Add 'Dessert' tag to recipe.
        # Recipe now has: [Dessert] 🏷️

        payload = {'tags': []}
        # "Remove ALL tags from this recipe!"
        # Empty list [] = clear everything! 🗑️

        url = detail_url(recipe.id)
        # Get the URL for this specific recipe
        # e.g. /api/recipes/1/

        res = self.client.patch(url, payload, format='json')
        # Send PATCH request to clear all tags.
        # format='json' needed because tags is nested data.

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # 200 = "Updated successfully!" ✅

        recipe.refresh_from_db()
        # Reload recipe from database to get latest values.
        # Without this recipe still shows [Dessert] in memory
        # even if database already cleared it! 🔄

        self.assertEqual(recipe.tags.count(), 0)
        # "Does this recipe have ZERO tags now?" ✅
        # count() = 0 means all tags cleared successfully! 🗑️✅

    def test_create_recipe_with_new_ingredients(self):
        """Test creating a recipe with new ingredients."""

        payload = {
            'title': 'Cauliflower Tacos',
            'time_minutes': 60,
            'price': Decimal('4.30'),
            'ingredients': [
                {'name': 'Cauliflower'},
                {'name': 'Salt'},
            ],
        }

        res = self.client.post(
            RECIPES_URL,
            payload,
            format='json'
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipe = Recipe.objects.get(id=res.data['id'])

        self.assertEqual(recipe.ingredients.count(), 2)

        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user,
            ).exists()

            self.assertTrue(exists)

    def test_create_recipe_with_existing_ingredient(self):
        """Test creating a new recipe with existing ingredient."""
        ingredient = Ingredient.objects.create(user=self.user, name='Lemon')
        payload = {
            'title': 'Vietnamese Soup',
            'time_minutes': 25,
            'price': '2.55',
            'ingredients': [{'name': 'Lemon'}, {'name': 'Fish Sauce'}]
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingredient, recipe.ingredients.all())
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_ingredient_on_update(self):
        """Test creating an ingredient when updating a recipe."""
        recipe = create_recipe(user=self.user)

        payload = {
            'ingredients': [
                {'name': 'Limes'}
            ]
        }

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        new_ingredient = Ingredient.objects.get(
            user=self.user,
            name='Limes',
        )

        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_update_recipe_assign_ingredient(self):
        """Test assigning an existing ingredient when updating."""

        ingredient1 = Ingredient.objects.create(
            user=self.user,
            name='Pepper',
        )

        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient1)

        ingredient2 = Ingredient.objects.create(
            user=self.user,
            name='Chili',
        )

        payload = {
            'ingredients': [
                {'name': 'Chili'}
            ]
        }

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        recipe.refresh_from_db()

        self.assertIn(ingredient2, recipe.ingredients.all())
        self.assertNotIn(ingredient1, recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        """Test clearing a recipe's ingredients."""
        ingredient = Ingredient.objects.create(
            user=self.user,
            name='Garlic'
        )

        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)

        payload = {'ingredients': []}

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        recipe.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)

    def test_filter_by_tags(self):
        """Test filtering recipes by tags."""
        r1 = create_recipe(user=self.user, title='Thai Vegetable Curry')
        r2 = create_recipe(user=self.user, title='Aubergine with Tahini')
        tag1 = Tag.objects.create(user=self.user, name='Vegan')
        tag2 = Tag.objects.create(user=self.user, name='Vegetrian')
        r1.tags.add(tag1)
        r2.tags.add(tag2)
        r3 = create_recipe(user=self.user, title='Fish and chips')

        params = {'tags': f'{tag1.id},{tag2.id}'}
        res = self.client.get(RECIPES_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)
        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)

    def test_filter_by_ingredients(self):
        """Test filtering recipes by ingredients."""
        r1 = create_recipe(user=self.user, title='Posh Beans on Toast')
        r2 = create_recipe(user=self.user, title='Chicken Cacciatore')
        r3 = create_recipe(user=self.user, title='Red Lentil Daal')

        in1 = Ingredient.objects.create(user=self.user, name='Feta Cheese')
        in2 = Ingredient.objects.create(user=self.user, name='Chicken')
        r1.ingredients.add(in1)
        r2.ingredients.add(in2)

        params = {'ingredients': f'{in1.id},{in2.id}'}
        res = self.client.get(RECIPES_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)
        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)


class ImageUploadTests(TestCase):
    """Tests for the image upload API."""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'user@example.com',
            'password123',
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image(self):
        """Test uploading an image to a recipe."""
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10, 10))
            img.save(image_file, format='JPEG')
            image_file.seek(0)
            payload = {'image': image_file}
            res = self.client.post(url, payload, format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading invalid image."""
        url = image_upload_url(self.recipe.id)
        payload = {'image': 'notanimage'}
        res = self.client.post(url, payload, "multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
