from django import template

register = template.Library()

@register.filter
def class_name(value):
    return str(value.__class__)
