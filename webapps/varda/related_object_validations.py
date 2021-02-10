import datetime
import logging

from collections import namedtuple
from django.db.models import Q
from rest_framework.exceptions import ValidationError

from varda.enums.error_messages import ErrorMessages
from varda.models import (VakaJarjestaja, Henkilo, Varhaiskasvatuspaatos, Varhaiskasvatussuhde, Lapsi, Huoltaja,
                          Z3_AdditionalCasUserFields, Z4_CasKayttoOikeudet, Palvelussuhde, Tyoskentelypaikka,
                          PidempiPoissaolo, ToiminnallinenPainotus, KieliPainotus)

# Get an instance of a logger
logger = logging.getLogger(__name__)


DateRange = namedtuple('DateRange', ['start_date', 'end_date'])


def create_date_range(start_date, end_date):
    """Creates a DateRange object with given start and end dates """
    if not isinstance(start_date, datetime.date):  # if start_date is a datetime.date object, use it
        try:
            start_date = datetime.datetime.strptime(start_date.replace('-', ''), '%Y%m%d').date()
        except Exception:
            start_date = datetime.date(1000, 1, 1)  # use this date, if no valid date in correct format is given
    if not isinstance(end_date, datetime.date):  # if end_date is a datetime.date object, use it
        try:
            end_date = datetime.datetime.strptime(end_date.replace('-', ''), '%Y%m%d').date()
        except Exception:
            end_date = datetime.date(3000, 1, 1)  # use this date, if no valid date in correct format is given (e.g. None)
    if start_date > end_date:
        raise ValidationError({'paattymis_pvm': [ErrorMessages.MI004.value]})
    return DateRange(start_date=start_date, end_date=end_date)


def date_range_overlap(range1, range2):
    latest_start = max(range1.start_date, range2.start_date)
    earliest_end = min(range1.end_date, range2.end_date)
    overlap_in_days = (earliest_end - latest_start).days + 1
    if overlap_in_days > 0:
        return True
    else:
        return False


def check_if_url_is_valid(list_of_url_segments, model):
    """
    url examples:
     - Absolute: http://localhost:8000/api/v1/vakajarjestajat/6/ ==> ['http:', '', 'localhost:8000', 'api', 'v1', 'vakajarjestajat', '6', '']
     - Relative: /api/v1/vakajarjestajat/6/ ==> ['', 'api', 'v1', 'vakajarjestajat', '6', '']
    """
    if (len(list_of_url_segments) > 1 and
        ((list_of_url_segments[0].startswith(('http', 'https')) and len(list_of_url_segments) != 8) or
            (list_of_url_segments[0] == '' and list_of_url_segments[1] == 'api' and len(list_of_url_segments) != 6))):
        raise ValidationError({model: [ErrorMessages.GE009.value]})


def check_if_is_owner_of_related_object(list_of_url_segments, user, model):
    """
    See an example of url segments above.
    """
    related_object_id = list_of_url_segments[-2]
    if user != model.objects.get(id=related_object_id).changed_by:
        raise ValidationError({model: [ErrorMessages.GE008.value]})


def check_if_user_has_add_toimipaikka_permissions_under_vakajarjestaja(vakajarjestaja_id, user):
    """
    User must have TALLENTAJA permissions on the vakajarjestaja-level.
    Or user must be "palvelukayttaja".
    """
    validation_error_msg = {'errors': [ErrorMessages.TP009.value]}
    try:
        user_details = Z3_AdditionalCasUserFields.objects.get(user=user)
    except Z3_AdditionalCasUserFields.DoesNotExist:
        raise ValidationError(validation_error_msg)

    if user_details.kayttajatyyppi == 'PALVELU':
        return None

    # Kayttaja == "VIRKAILIJA"
    vakajarjestaja = VakaJarjestaja.objects.get(id=vakajarjestaja_id)
    organisaatio_oid = vakajarjestaja.organisaatio_oid
    if (not Z4_CasKayttoOikeudet.objects
                                .filter(user_id=user.id)
                                .filter(organisaatio_oid=organisaatio_oid)
                                .filter(kayttooikeus=Z4_CasKayttoOikeudet.TALLENTAJA)
                                .exists()):
        raise ValidationError(validation_error_msg)


def check_if_user_has_access_to_henkilo(url, user):
    model = Henkilo
    list_of_url_segments = url.split('/')
    check_if_url_is_valid(list_of_url_segments, model)

    henkilo_id = list_of_url_segments[-2]
    henkilo = Henkilo.objects.get(id=henkilo_id)
    if not user.has_perm('view_henkilo', henkilo):
        raise ValidationError({'henkilo': [ErrorMessages.GE008.value]})


def check_if_henkilo_is_changed(path, uusi_henkilo_id, user):
    """
    Only admin can change the identity of the Lapsi/Työntekijä/Huoltaja.
    """
    model = Henkilo
    list_of_path_segments = path.split('/')  # Path e.g. /api/v1/henkilot/99/
    check_if_url_is_valid(list_of_path_segments, model)
    rooli_id = list_of_path_segments[-2]

    if user.is_superuser:
        return None

    if 'huoltajat' in path:
        nykyinen_henkilo_id = Huoltaja.objects.get(id=rooli_id).henkilo.id
    elif 'lapset' in path:
        nykyinen_henkilo_id = Lapsi.objects.get(id=rooli_id).henkilo.id

    if uusi_henkilo_id != nykyinen_henkilo_id:
        raise ValidationError({'henkilo': [ErrorMessages.GE013.value]})


def check_if_admin_mutable_object_is_changed(user, instance, data, key, **kwargs):
    if user.is_superuser:
        return None

    check_if_immutable_object_is_changed(instance, data, key, **kwargs)


def check_if_immutable_object_is_changed(instance, data, key, attr=None, many=False):
    if attr is None:
        def get_id(x):
            return x.id
        attr = get_id

    if key in data:
        if not many:
            if attr(data[key]) != attr(getattr(instance, key)):
                msg = ({key: [ErrorMessages.GE013.value]})
                raise ValidationError(msg, code='invalid')
        else:
            datas = [attr(elem[key]) for elem in data]
            instances = [attr(getattr(instance, key)) for elem in instance]
            if datas != instances:
                msg = ({key: [ErrorMessages.GE013.value]})
                raise ValidationError(msg, code='invalid')


def _check_overlapping_object(model, parent_path, limit, error, data, extra_filters=(), self_id=None):
    """
    Generic function to check if maximum number of overlapping objects by date (alkamis_pvm, paattymis_pvm) is
    exceeded. Raises ValidationError if overlap is detected.

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
        filter_key += f'__{path_child}'
    filter_object = Q(**{filter_key: parent_object.id})
    if self_id:
        # PUT or PATCH so do not include self to evaluation
        filter_object &= ~Q(pk=self_id)
    for filter_attribute in extra_filters:
        # Apply extra filters
        self_value = data[filter_attribute] if filter_attribute in data else getattr(original_object, filter_attribute)
        filter_object &= Q(**{filter_attribute: self_value})

    qs = model.objects.filter(filter_object)
    alkamis_pvm_new, paattymis_pvm_new = _get_alkamis_paattymis_pvm(data, original_object)
    date_range_new = create_date_range(alkamis_pvm_new, paattymis_pvm_new)

    counter = 1
    for instance in qs:
        date_range_instance = create_date_range(instance.alkamis_pvm, instance.paattymis_pvm)
        if date_range_overlap(date_range_instance, date_range_new):
            counter += 1
    if counter > limit:
        raise ValidationError({'errors': [error]})


def _get_alkamis_paattymis_pvm(data, original):
    alkamis_pvm = data['alkamis_pvm'] if 'alkamis_pvm' in data else original.alkamis_pvm
    if 'paattymis_pvm' in data:
        paattymis_pvm = data['paattymis_pvm']
    elif original:
        paattymis_pvm = original.paattymis_pvm
    else:
        paattymis_pvm = None
    return alkamis_pvm, paattymis_pvm


def check_overlapping_toiminnallinen_painotus(data, self_id=None):
    _check_overlapping_object(ToiminnallinenPainotus, ['toimipaikka'], 1, ErrorMessages.TO001.value, data,
                              extra_filters=['toimintapainotus_koodi'], self_id=self_id)


def check_overlapping_kielipainotus(data, self_id=None):
    _check_overlapping_object(KieliPainotus, ['toimipaikka'], 1, ErrorMessages.KP001.value, data,
                              extra_filters=['kielipainotus_koodi'], self_id=self_id)


def check_overlapping_varhaiskasvatuspaatos(data, self_id=None):
    _check_overlapping_object(Varhaiskasvatuspaatos, ['lapsi'], 3, ErrorMessages.VP011.value, data, self_id=self_id)


def check_overlapping_varhaiskasvatussuhde(data, self_id=None):
    _check_overlapping_object(Varhaiskasvatussuhde, ['varhaiskasvatuspaatos', 'lapsi'], 3, ErrorMessages.VS013.value,
                              data, self_id=self_id)


def check_overlapping_palvelussuhde(data, self_id=None):
    _check_overlapping_object(Palvelussuhde, ['tyontekija'], 7, ErrorMessages.PS006.value, data, self_id=self_id)


def check_overlapping_tyoskentelypaikka(data, self_id=None):
    _check_overlapping_object(Tyoskentelypaikka, ['palvelussuhde'], 3, ErrorMessages.TA011.value, data, self_id=self_id)


def check_overlapping_pidempi_poissaolo(data, self_id=None):
    _check_overlapping_object(PidempiPoissaolo, ['palvelussuhde'], 1, ErrorMessages.PP007.value, data, self_id=self_id)


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

    if toimipaikka_oid is None or toimipaikan_nimi.startswith('Palveluseteli ja ostopalvelu'):
        return False

    return True


def check_toimipaikka_and_vakajarjestaja_have_oids(toimipaikka_obj, vakajarjestaja_organisaatio_oid, toimipaikka_organisaatio_oid):
    toimipaikka_id = toimipaikka_obj.id
    if (vakajarjestaja_organisaatio_oid == '' or
            (toimipaikka_is_valid_to_organisaatiopalvelu(toimipaikka_obj=toimipaikka_obj) and toimipaikka_organisaatio_oid == '')):
        logger.error('Missing organisaatio_oid(s) for toimipaikka: ' + str(toimipaikka_id))
        raise ValidationError({'errors': [ErrorMessages.MI002.value]})
