"""
Django admin customization
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
# _ is a shortcut for translation - turns text into the user's language
# automatically
from django.utils.translation import gettext_lazy as _
from core import models


class UserAdmin(BaseUserAdmin):
    """Define the admin pages for users"""

    # Sort users by id (1, 2, 3...) in the list page
    ordering = ['id']

    # Show these two columns in the users list page
    list_display = ['email', 'name']

    # fieldsets = sections on the user detail page (when you click on a user)
    fieldsets = (
        # Section 1: no title, shows email and password
        (None, {'fields': ('email', 'password')}),

        # Section 2: titled "Permissions", shows account permission checkboxes
        (
            _('Permissions'),
            {
                'fields': (
                    'is_active',    # is this account turned on?
                    'is_staff',     # can they access the admin panel?
                    'is_superuser',  # are they the boss with full access?
                )
            }
        ),

        # Section 3: titled "Important dates", shows last login time
        (_('Important dates'), {'fields': ('last_login',)}),
    )

    # last_login is view only - Django updates it automatically, nobody edits
    # it manually
    readonly_fields = ['last_login']
    add_fieldsets = (
        (None, {                    # None = no title for this section
            # makes the form wider on the page (just styling)
            'classes': ('wide',),
            'fields': (
                'email',
                'password1',        # enter password
                'password2',        # confirm password (type it again)
                'name',
                'is_active',        # is account turned on?
                'is_staff',         # can they access admin panel?
                'is_superuser',     # are they the boss with full access?
            )
        }),  # comma = this section is done
    )        # closes the whole add_fieldsets


# Register our custom UserAdmin so Django uses our rules, not the defaults
admin.site.register(models.User, UserAdmin)
admin.site.register(models.Recipe)
admin.site.register(models.Tag)
admin.site.register(models.Ingredient)
