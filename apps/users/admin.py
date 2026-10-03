"""Admin registration for users."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

from apps.users.models import User


class UserCreationForm(AdminUserCreationForm):
    """Admin form for adding a user."""

    class Meta:
        model = User
        fields = ("email", "name")


class UserEditForm(UserChangeForm):
    """Admin form for editing a user."""

    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin for the email-based user model."""

    form = UserEditForm
    add_form = UserCreationForm
    list_display = ("email", "name", "is_staff", "is_active", "last_login")
    readonly_fields = ("last_login", "date_joined")
    search_fields = ("email", "name")
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("name",)}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "name",
                    "usable_password",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
