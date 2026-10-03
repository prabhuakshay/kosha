"""Write amounts in templates: ``{{ amount|money }}``."""

from django import template

from apps.core.money import write

register = template.Library()
register.filter("money", write)
