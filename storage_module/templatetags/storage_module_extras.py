import json

from django import template
from django.apps import apps as django_apps

register = template.Library()


@register.filter
def make_range(n):
    return range(n)


@register.simple_tag
def is_instance(obj, model_name):
    model = django_apps.get_model(app_label='storage_module', model_name=model_name)
    return isinstance(obj, model)


@register.filter
def hasattr(obj, attr):
    return hasattr(obj, attr)


@register.filter('parse_json')
def parse_json(value):
    return json.loads(value)


@register.filter
def get_item(dictionary, key):
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    else:
        return None
