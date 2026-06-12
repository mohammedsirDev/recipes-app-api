"""
Tests for the Django admin modifications.
"""

# Importing tools we need
from django.test import TestCase          # Lets us write and run tests
# Gets our User model (the user blueprint)
from django.contrib.auth import get_user_model
from django.urls import reverse           # Converts page names into real URLs
# A fake browser that visits pages for us
from django.test import Client


class AdminSiteTests(TestCase):
    """Tests for Django admin."""

    def setUp(self):
        """
        This runs BEFORE every test automatically.
        Like setting up the table before eating.
        """

        # Create a fake browser that will visit pages during tests
        self.client = Client()

        # Create a fake ADMIN user (the boss - has full access to everything)
        self.admin_user = get_user_model().objects.create_superuser(
            email='admin@example.com',
            password='testpass123',
        )

        # Log the fake browser in as the admin
        # force_login = skip the login page, just go straight in
        self.client.force_login(self.admin_user)

        # Create a fake NORMAL user (not admin, just a regular account)
        # This is the person we will LOOK FOR in the admin panel
        self.user = get_user_model().objects.create_user(
            email='user@example.com',
            password='testpass123',
            name='Test User'
        )

    def test_users_list(self):
        """Test that users are listed on page"""

        # Get the URL of the admin page that lists ALL users
        # 'admin'        = Django's built-in admin panel
        # 'core'         = our app name
        # 'user'         = our User model name
        # 'changelist'   = the page that LISTS all records
        url = reverse('admin:core_user_changelist')

        # Make the fake browser VISIT that URL
        # res = the page content we get back (short for response)
        res = self.client.get(url)

        # Check that 'Test User' is visible somewhere on the page
        # If not found -> test FAILS
        self.assertContains(res, self.user.name)

        # Check that 'user@example.com' is visible somewhere on the page
        # If not found -> test FAILS
        self.assertContains(res, self.user.email)

        # If BOTH are found -> test PASSES ✅

    def test_edit_user_page(self):
        """Test the edit user page works."""
        url = reverse('admin:core_user_change', args=[self.user.id])
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)

    def test_create_user_page(self):
        """Test the create user page works."""

        # Get the URL of the "Add New User" page in the admin panel
        url = reverse('admin:core_user_add')

        # Make the fake browser visit that page
        res = self.client.get(url)

        # Check the page loaded successfully
        # 200 = OK ✅  |  404 = not found ❌  |  500 = crashed ❌
        self.assertEqual(res.status_code, 200)
