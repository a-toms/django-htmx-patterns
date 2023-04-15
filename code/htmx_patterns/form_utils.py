from functools import wraps

from django.forms import Form
from django.forms.widgets import CheckboxInput
from django.http import HttpResponse
from django.http.request import QueryDict


def htmx_form_validate(*, form_class: type):
    """
    Instead of a normal view, just do htmx validation using the given form class,
    for a single field and return the single div that needs to be replaced.
    Normally the form class will be the same class used in the view body.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if (
                request.method == "POST"
                and "Hx-Request" in request.headers
                and (htmx_validation_field := request.POST.get("_validate_field", None))
            ):
                form = _build_validation_form(form_class, request.POST, htmx_validation_field)
                form.is_valid()  # trigger validation
                return HttpResponse(render_single_field_row(form, htmx_validation_field))
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def render_single_field_row(form: Form, field_name: str):
    # Assumes form has renderer with `single_field_row_template` defined
    bound_field = form[field_name]
    return form.render(
        context={
            "field": bound_field,
            "errors": form.error_class(bound_field.errors, renderer=form.renderer),
            "do_htmx_validation": form.do_htmx_validation,
        },
        template_name=form.renderer.single_field_row_template,
    )


def _build_validation_form(form_class: type[Form], data: QueryDict, field_name: str):
    # htmx quirk: when using hx-params, it submits "undefined" for checkboxes that are unchecked,
    # instead of omitting the field like we expect. We want to keep using params, to avoid submitting
    # fields that are not relevant to individual field validation, so we fix here.
    field = form_class.base_fields[field_name]
    if isinstance(field.widget, CheckboxInput):
        if data.get(field_name) == "undefined":
            data = data.copy()
            del data[field_name]  # checkbox value is False
    return form_class(data)
