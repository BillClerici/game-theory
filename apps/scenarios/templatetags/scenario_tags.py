from django import template

register = template.Library()


@register.filter
def get_item(dictionary: dict, key: str):
    """Lookup a dict value by key in templates: {{ mydict|get_item:key }}"""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None
