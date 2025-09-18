import datetime
import logging

from collections import namedtuple
from operator import itemgetter

from django.db.models import Q
from rest_framework.exceptions import ValidationError

from varda.enums.error_messages import ErrorMessages
from varda.models import (
    Varhaiskasvatuspaatos,
    Varhaiskasvatussuhde,
    Palvelussuhde,
    Tyoskentelypaikka,
    PidempiPoissaolo,
    ToiminnallinenPainotus,
    KieliPainotus,
    Maksutieto,
)


logger = logging.getLogger(__name__)


DateRange = namedtuple("DateRange", ["start_date", "end_date"])


def create_date_range(start_date, end_date):
    """Creates a DateRange object with given start and end dates"""
    if not isinstance(start_date, datetime.date):  # if start_date is a datetime.date object, use it
        try:
            start_date = datetime.datetime.strptime(start_date.replace("-", ""), "%Y%m%d").date()
        except Exception:
            start_date = datetime.date(1000, 1, 1)  # use this date, if no valid date in correct format is given
    if not isinstance(end_date, datetime.date):  # if end_date is a datetime.date object, use it
        try:
            end_date = datetime.datetime.strptime(end_date.replace("-", ""), "%Y%m%d").date()
        except Exception:
            end_date = datetime.date(3000, 1, 1)  # use this date, if no valid date in correct format is given (e.g. None)
    if start_date > end_date:
        raise ValidationError({"paattymis_pvm": [ErrorMessages.MI004.value]})
    return DateRange(start_date=start_date, end_date=end_date)


def date_range_overlap(range1, range2):
    latest_start = max(range1.start_date, range2.start_date)
    earliest_end = min(range1.end_date, range2.end_date)
    overlap_in_days = (earliest_end - latest_start).days + 1
    if overlap_in_days > 0:
        return True
    else:
        return False


def check_if_admin_mutable_object_is_changed(user, instance, data, key, **kwargs):
    if user.is_superuser:
        return None

    check_if_immutable_object_is_changed(instance, data, key, **kwargs)


def check_if_immutable_object_is_changed(instance, data, key, compare_id=True):
    """
    Use this function to determine if some value has changed in PUT/PATCH requests compared to the existing object.
    By default id-field is used in comparison (e.g. id of Lapsi, Organisaatio, Toimipaikka...), use compare_id=False
    to compare values directly.
    :param instance: object instance
    :param data: new data dictionary
    :param key: key to compare
    :param compare_id: pass True if you want to compare the values directly
    """
    if compare_id:

        def compare_function(value):
            return getattr(value, "id", None)

    else:

        def compare_function(value):
            return value

    compare_value_getter = compare_function

    if key in data:
        new_value = compare_value_getter(data[key])
        if isinstance(new_value, str):
            new_value = new_value.lower()

        old_value = compare_value_getter(getattr(instance, key))
        if isinstance(old_value, str):
            old_value = old_value.lower()

        if new_value != old_value:
            msg = {key: [ErrorMessages.GE013.value]}
            raise ValidationError(msg, code="invalid")


def _find_overlap_for_period(start_date, end_date, date_pair_list, limit, error):
    """
    Find overlapping objects. If number of overlapping objects exceeds limit, raise an error.
    :param start_date: alkamis_pvm of new object
    :param end_date: paattymis_pvm of new object
    :param date_pair_list: list of (alkamis_pvm, paattymis_pvm,) tuples of existing objects
    :param limit: threshold limit
    :param error: error message
    """
    # Add new dates to the list
    date_pair_list.append((start_date, end_date))

    # Create tuples containing date and type of the date (alkamis_pvm=1, paattymis_pvm=2)
    date_list = []
    for date_pair in date_pair_list:
        date_list.append((date_pair[0], 1))
        if date_pair[1]:
            # paattymis_pvm can be None, in which case do not add it to the list
            date_list.append((date_pair[1], 2))

    # Sort the list of dates, ordering alkamis_pvm before paattymis_pvm
    date_list.sort(key=itemgetter(0, 1))

    counter = 0
    for date_instance in date_list:
        date_value = date_instance[0]
        date_type = date_instance[1]

        if date_type == 1:
            # alkamis_pvm
            counter += 1
        elif date_type == 2:
            # paattymis_pvm
            counter -= 1

        if (date_value >= start_date and (not end_date or date_value <= end_date)) and counter > limit:
            # If current date is between start_date and end_date, validate overlap
            raise ValidationError({"errors": [error]})


def _check_overlapping_object(model, parent_path, limit, error, data, extra_filters=(), self_id=None):
    """
    Generic function to check if maximum number of overlapping objects by date (alkamis_pvm, paattymis_pvm) is
    exceeded.
    :param model: Model class
    :param parent_path: list of attributes to reach parent with which overlap is evaluated
                        (e.g Lapsi can have 3 overlapping Varhaiskasvatussuhde,
                        path is ['varhaiskasvatuspaatos', 'lapsi'])
    :param limit: int describing how many overlapping objects there can be
    :param error: ErrorMessages value
    :param extra_filters: list of attributes that also need to be equal to count as overlap
                          (e.g. ['kielipainotus_koodi'])
    :param data: validated_data from Serializer
    :param self_id: id if object already has one (PUT, PATCH)
    """
    original_object = model.objects.get(id=self_id) if self_id else None

    path_child = parent_path[0]
    parent_object = data[path_child] if path_child in data else getattr(original_object, path_child)
    filter_key = path_child
    for path_child in parent_path[1:]:
        parent_object = getattr(parent_object, path_child)
        filter_key += f"__{path_child}"
    filter_object = Q(**{filter_key: parent_object.id})
    if self_id:
        # PUT or PATCH so do not include self to evaluation
        filter_object &= ~Q(pk=self_id)
    for filter_attribute in extra_filters:
        # Apply extra filters
        self_value = data[filter_attribute] if filter_attribute in data else getattr(original_object, filter_attribute)
        filter_object &= Q(**{filter_attribute: self_value})

    alkamis_pvm_new, paattymis_pvm_new = _get_alkamis_paattymis_pvm(data, original_object)

    # Only include objects that end after new object has started
    qs = model.objects.filter(filter_object & (Q(paattymis_pvm__isnull=True) | Q(paattymis_pvm__gte=alkamis_pvm_new))).distinct(
        "id"
    )
    date_pair_list = list(qs.values_list("alkamis_pvm", "paattymis_pvm"))

    _find_overlap_for_period(alkamis_pvm_new, paattymis_pvm_new, date_pair_list, limit, error)


def _get_alkamis_paattymis_pvm(data, original):
    alkamis_pvm = data["alkamis_pvm"] if "alkamis_pvm" in data else original.alkamis_pvm
    if "paattymis_pvm" in data:
        paattymis_pvm = data["paattymis_pvm"]
    elif original:
        paattymis_pvm = original.paattymis_pvm
    else:
        paattymis_pvm = None
    return alkamis_pvm, paattymis_pvm


def check_overlapping_toiminnallinen_painotus(data, self_id=None):
    _check_overlapping_object(
        ToiminnallinenPainotus,
        ["toimipaikka"],
        1,
        ErrorMessages.TO001.value,
        data,
        extra_filters=["toimintapainotus_koodi"],
        self_id=self_id,
    )


def check_overlapping_kielipainotus(data, self_id=None):
    _check_overlapping_object(
        KieliPainotus, ["toimipaikka"], 1, ErrorMessages.KP001.value, data, extra_filters=["kielipainotus_koodi"], self_id=self_id
    )


def check_overlapping_varhaiskasvatuspaatos(data, self_id=None):
    _check_overlapping_object(Varhaiskasvatuspaatos, ["lapsi"], 3, ErrorMessages.VP011.value, data, self_id=self_id)


def check_overlapping_varhaiskasvatussuhde(data, self_id=None):
    _check_overlapping_object(
        Varhaiskasvatussuhde, ["varhaiskasvatuspaatos", "lapsi"], 3, ErrorMessages.VS013.value, data, self_id=self_id
    )


def check_overlapping_maksutieto(data, self_id=None):
    _check_overlapping_object(Maksutieto, ["huoltajuussuhteet", "lapsi"], 2, ErrorMessages.MA004.value, data, self_id=self_id)


def check_overlapping_palvelussuhde(data, self_id=None):
    _check_overlapping_object(Palvelussuhde, ["tyontekija"], 7, ErrorMessages.PS006.value, data, self_id=self_id)


def check_overlapping_tyoskentelypaikka(data, self_id=None):
    _check_overlapping_object(Tyoskentelypaikka, ["palvelussuhde"], 3, ErrorMessages.TA011.value, data, self_id=self_id)


def check_overlapping_pidempi_poissaolo(data, self_id=None):
    _check_overlapping_object(PidempiPoissaolo, ["palvelussuhde"], 1, ErrorMessages.PP007.value, data, self_id=self_id)


def toimipaikka_is_valid_to_organisaatiopalvelu(toimipaikka_obj=None, nimi=None):
    """
    There are a few special cases currently, where the toimipaikka is not to be POSTed to Org.palvelu.
    """
    if toimipaikka_obj is None:
        toimipaikan_nimi = nimi
        toimipaikka_oid = None
    else:
        toimipaikan_nimi = toimipaikka_obj.nimi
        toimipaikka_oid = toimipaikka_obj.organisaatio_oid

    if toimipaikka_oid is None or toimipaikan_nimi.startswith("Palveluseteli ja ostopalvelu"):
        return False

    return True


def check_toimipaikka_and_vakajarjestaja_have_oids(
    toimipaikka_obj, vakajarjestaja_organisaatio_oid, toimipaikka_organisaatio_oid
):
    toimipaikka_id = toimipaikka_obj.id
    if vakajarjestaja_organisaatio_oid == "" or (
        toimipaikka_is_valid_to_organisaatiopalvelu(toimipaikka_obj=toimipaikka_obj) and toimipaikka_organisaatio_oid == ""
    ):
        logger.error("Missing organisaatio_oid(s) for toimipaikka: " + str(toimipaikka_id))
        raise ValidationError({"errors": [ErrorMessages.MI002.value]})
