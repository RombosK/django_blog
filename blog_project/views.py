from django.http import HttpResponseServerError
from django.template import loader
from django.views.defaults import server_error

def custom_server_error(request, template_name='500.html'):
    """Кастомная страница 500 ошибки"""
    try:
        template = loader.get_template(template_name)
        return HttpResponseServerError(template.render({}, request))
    except Exception:
        # Если кастомный шаблон недоступен, используем стандартный
        return server_error(request)