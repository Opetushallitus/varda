from django.apps import apps
from django.db.models import Model


def _get_code_translation(code_list, code):
    if not code:
        return None
    for code_list_item in code_list:
        if code_list_item.get("code_value").lower() == code.lower():
            return f'{code_list_item.get("name")} ({code.lower()})'
    return code


def _get_json_code_translation(code_list, code):
    if not code:
        return None
    for code_list_item in code_list:
        if code_list_item.get("code_value").lower() == code.lower():
            return {"koodi": code, "nimi": code_list_item.get("name")}
    return {"koodi": code, "nimi": None}


def _get_multiple_code_translations(code_list, code_value_list):
    return ", ".join([_get_code_translation(code_list, code_value) for code_value in code_value_list])


def _get_dates_for_model_and_id(model_name, model_id):
    app_config = apps.get_app_config("varda")
    model = app_config.get_model(model_name)
    if isinstance(model(), Model):
        if model_instance := model.objects.filter(id=model_id).first():
            if hasattr(model_instance, "alkamis_pvm") and hasattr(model_instance, "paattymis_pvm"):
                alkamis_pvm = model_instance.alkamis_pvm.strftime("%d.%m.%Y") if model_instance.alkamis_pvm else ""
                paattymis_pvm = model_instance.paattymis_pvm.strftime("%d.%m.%Y") if model_instance.paattymis_pvm else ""
                return f"{alkamis_pvm}-{paattymis_pvm}"


def _get_nested_value(nested_dict, value_path, value_key, default_value=0):
    temp_dict = nested_dict
    for path_key in value_path:
        temp_dict = temp_dict.get(path_key, {})
    return temp_dict.get(value_key, default_value)
