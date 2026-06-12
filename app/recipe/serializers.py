"""
Serializers for recipe APIs
"""

# DRF's serializer module for data validation & conversion
from rest_framework import serializers

# Import the Recipe model to serialize
from core.models import Recipe, Tag, Ingredient


class IngredientSerializer(serializers.ModelSerializer):
    """Serializer for ingredients."""

    class Meta:
        model = Ingredient
        fields = ['id', 'name']
        read_only_fields = ['id']


class TagSerializer(serializers.ModelSerializer):
    """Serializer for tags"""

    class Meta:
        model = Tag
        fields = ['id', 'name']
        read_only_fields = ['id']


class RecipeSerializer(serializers.ModelSerializer):
    """
    Serializer for recipes.
    Converts Recipe model instances to/from JSON for API request and response handling.
    ModelSerializer auto-generates fields and validators based on the model.
    """
    ingredients = IngredientSerializer(many=True, required=False)

    tags = TagSerializer(many=True, required=False)
    # Tell the serializer that this recipe CAN have tags.
    # many=True     = tags is a LIST not just one tag
    #                 e.g. [{'name': 'Indian'}, {'name': 'Breakfast'}]
    # required=False = tags is OPTIONAL — recipe can be created
    #                  without any tags at all. 😄

    class Meta:
        """
        Meta class defines the model and fields to include in serialization.
        """
        model = Recipe  # The model this serializer is based on

        fields = [
            'id',
            'title',
            'time_minutes',
            'price',
            'link',
            'tags',
            'ingredients']
        read_only_fields = ['id']
        # 'id' is read-only: it's auto-assigned by the database and should
        # never be manually set or modified via API input

    def _get_or_create_tags(self, tags, recipe):
        """Handle getting or creating tags as needed."""
        # Private helper method — starts with _ meaning
        # only used INSIDE this class, not from outside! 🔒
        # Called by both create() and update() to avoid
        # repeating the same tag logic twice. DRY! 😄

        auth_user = self.context['request'].user
        # Who is making this request? 👤
        # Tags must belong to the correct user.

        for tag in tags:
            # Loop through each tag one by one.
            # e.g. [{'name':'Lunch'}, {'name':'Dinner'}]

            tag_obj, created = Tag.objects.get_or_create(
                user=auth_user,  # tag must belong to this user 👤
                **tag,           # {'name':'Lunch'} → name='Lunch' 🎁
            )
            # Smart database check 🧠:
            # tag exists?  → reuse it   ♻️  created=False
            # tag missing? → create it  ✨  created=True
            # created variable ignored — we only need tag_obj 😄

            recipe.tags.add(tag_obj)
            # Link tag to recipe 🔗
            # Like adding topping to burger 🍔

    def _get_or_create_ingredients(self, ingredients, recipe):
        """Handle getting or creating ingredients as needed."""
        auth_user = self.context['request'].user

        for ingredient in ingredients:
            ingredient_obj, created = Ingredient.objects.get_or_create(
                user=auth_user,
                **ingredient,
            )

            recipe.ingredients.add(ingredient_obj)

    def create(self, validated_data):
        """Create a recipe."""
        # Runs on POST /api/recipes/
        # Custom create needed because default Django
        # create() crashes with nested tags! 💥

        tags = validated_data.pop('tags', [])
        ingredients = validated_data.pop('ingredients', [])
        recipe = Recipe.objects.create(**validated_data)
        # Remove tags from data before creating recipe.
        # [] = default if no tags sent — no crash! 😄
        # validated_data is now safe to use ✅

        # Create recipe WITHOUT tags first.
        # **validated_data unpacks dict → title=, price= etc

        self._get_or_create_tags(tags, recipe)
        self._get_or_create_ingredients(ingredients, recipe)
        # Handle all tag logic in helper method.
        # reuse existing tags ♻️ or create new ones ✨
        # then link them to recipe 🔗

        return recipe
        # Return complete recipe with all tags! 🎉

    def update(self, instance, validated_data):
        """Update recipe."""
        # Runs on PUT/PATCH /api/recipes/1/
        # instance = existing recipe in database 🍔
        # validated_data = new data to update with 🥬

        tags = validated_data.pop('tags', None)
        ingredients = validated_data.pop('ingredients', None)
        if ingredients is not None:
            instance.ingredients.clear()
            self._get_or_create_ingredients(ingredients, instance)
        # Remove tags — handle separately.
        # None = default this time (not [] like create!)
        #
        # None → tags not sent → leave tags alone! 😴
        # []   → empty sent   → clear all tags!   🗑️
        # [..] → tags sent    → update tags!      ✨

        if tags is not None:
            # User sent tags — handle them!
            instance.tags.clear()
            # Wipe ALL existing tags first 🗑️
            # Fresh start before adding new ones.

            self._get_or_create_tags(tags, instance)
            # Add new tags using helper method ✨
            # reuse ♻️ or create ✨ then link 🔗

        for attr, value in validated_data.items():
            # Loop through remaining fields:
            # attr  = field name  e.g. 'title'
            # value = new value   e.g. 'New Name'
            setattr(instance, attr, value)
            # Dynamically update each field 😄
            # Same as: instance.title = 'New Name'

        instance.save()
        # Save ALL changes to database 💾
        # Without this nothing gets saved!

        return instance
        # Return updated recipe — MUST have this! 🎉
        # Without return → DRF crashes! 💥


class RecipeDetailsSerializer(RecipeSerializer):
    """Serializer for recipe detail view."""
    # Inherits everything from RecipeSerializer — no need to redefine
    # fields, model, or read_only_fields. We just extend it.

    class Meta(RecipeSerializer.Meta):
        # Inherit the Meta class from RecipeSerializer (model, fields, read_only_fields)
        # so we don't repeat ourselves — only override what's different.

        fields = RecipeSerializer.Meta.fields + ['description']


class RecipeImageSerializer(serializers.ModelSerializer):
    """Serializer for uploading images to recipes."""

    class Meta:
        model = Recipe
        fields = ['id', 'image']
        read_only_fields = ['id']
        extra_kwargs = {'image': {'required': 'True'}}
