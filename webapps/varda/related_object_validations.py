import datetime
import logging

from collections import namedtuple
from django.db.models import Q
from rest_framework.exceptions import ValidationError

from varda.enums.error_messages import ErrorMessages
from varda.models import (VakaJarjestaja, Henkilo, Varhaiskasvatuspaatos, Varhaiskasvatussuhde, Lapsi, Huoltaja,
                          Z3_AdditionalCasUserFields, Z4_CasKayttoOikeudet, Palvelussuhde, Tyoskentelypaikka,
                          PidempiPoissaolo)

# Get an instance of a logger
logger = logging.getLogger(__name__)


DateRange = namedtuple('DateRange', ['start_date', 'end_date'])


def create_daterange(start_date, end_date):
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


def daterange_overlap(range1, range2):
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


def check_overlapping_koodi(validated_data, modelobj, *args):
    """
    Checks that there are no overlapping (same code at the overlapping time period) kielipainotus or
    toiminnallinenpainotus codes.
    """
    (model, koodi, overlap_error_message) = (('toiminnallinenpainotus', 'toimintapainotus_koodi', ErrorMessages.TO001.value)
                                             if 'toimintapainotus_koodi' in dir(modelobj) else
                                             ('kielipainotus', 'kielipainotus_koodi', ErrorMessages.KP001.value))
    if args:
        model_id, original = get_model_id_and_original(modelobj, args[0])
    else:
        model_id, original = get_model_id_and_original(modelobj)

    if args:  # for PUT/PATCH one needs to obtain the existing information, so the id needs to be given
        model_id = args[0]
        try:
            original = modelobj.objects.get(id=model_id)  # modelobj either KieliPainotus or ToiminnallinenPainotus
        except Exception:
            raise ValidationError({'errors': [ErrorMessages.GE016.value]})
    else:  # for POST one starts from scratch
        model_id = "0"
        original = None

    toimipaikka_id = validated_data['toimipaikka'].id if 'toimipaikka' in validated_data else original.toimipaikka.id
    data_koodi = validated_data[koodi] if koodi in validated_data else original[koodi]
    alkamis_pvm, paattymis_pvm = get_alkamis_paattymis_pvm(validated_data, original)
    daterange_new = create_daterange(alkamis_pvm, paattymis_pvm)
    queryset = modelobj.objects.filter(toimipaikka=toimipaikka_id)

    for item in queryset:
        code = item.toimintapainotus_koodi if 'toimintapainotus_koodi' in dir(item) else item.kielipainotus_koodi
        if item.id != int(model_id) and data_koodi == code:  # in case of update, do not compare to the record itself
            daterange_existing = create_daterange(item.alkamis_pvm, item.paattymis_pvm)
            overlapping = daterange_overlap(daterange_existing, daterange_new)
            if overlapping:
                raise ValidationError({'errors': [overlap_error_message]})


def check_overlapping_varhaiskasvatus_object(validated_data, modelobj, *args):
    """
    Checks that the number of varhaiskasvatussuhde or varhaiskasvatuspaatos during any time period is less than
    the given maximum
    """
    if args:
        model_id, original = get_model_id_and_original(modelobj, args[0])
    else:
        model_id, original = get_model_id_and_original(modelobj)

    if 'varhaiskasvatuspaatos' in dir(modelobj):  # Varhaiskasvatussuhde
        varhaiskasvatuspaatos_id = validated_data['varhaiskasvatuspaatos'].id if 'varhaiskasvatuspaatos' in validated_data else original.varhaiskasvatuspaatos.id
        lapsi_id = Varhaiskasvatuspaatos.objects.get(id=varhaiskasvatuspaatos_id).lapsi.id
        queryset = Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos__lapsi=lapsi_id)
        overlap_error_message = ErrorMessages.VS013.value
    else:  # Varhaiskasvatuspaatos
        lapsi_id = validated_data['lapsi'].id if 'lapsi' in validated_data else original.lapsi.id
        queryset = Varhaiskasvatuspaatos.objects.filter(lapsi=lapsi_id)
        overlap_error_message = ErrorMessages.VP011.value

    alkamis_pvm, paattymis_pvm = get_alkamis_paattymis_pvm(validated_data, original)
    daterange_new = create_daterange(alkamis_pvm, paattymis_pvm)
    MAX_OVERLAPS = 3
    counter = 1
    for item in queryset:
        if item.id != int(model_id):
            daterange_existing = create_daterange(item.alkamis_pvm, item.paattymis_pvm)
            overlap = daterange_overlap(daterange_existing, daterange_new)
            if overlap:
                counter += 1
    if counter > MAX_OVERLAPS:
        raise ValidationError({'errors': [overlap_error_message]})


def check_overlapping_palvelussuhde_object(validated_data, modelobj, *args):
    """
    Checks that the number of palvelussuhde during any time period is less than the maximum
    """
    if args:
        model_id, original = get_model_id_and_original(modelobj, args[0])
    else:
        model_id, original = get_model_id_and_original(modelobj)

    tyontekija_id = validated_data['tyontekija'].id if 'tyontekija' in validated_data else original.tyontekija.id

    if original is not None:
        q_obj = Q(Q(tyontekija=tyontekija_id) & ~Q(pk=original.id))
    else:
        q_obj = Q(tyontekija=tyontekija_id)

    queryset = Palvelussuhde.objects.filter(q_obj)

    alkamis_pvm, paattymis_pvm = get_alkamis_paattymis_pvm(validated_data, original)
    daterange_new = create_daterange(alkamis_pvm, paattymis_pvm)
    MAX_OVERLAPS = 7
    counter = 1
    for item in queryset:
        if item.id != int(model_id):
            daterange_existing = create_daterange(item.alkamis_pvm, item.paattymis_pvm)
            overlap = daterange_overlap(daterange_existing, daterange_new)
            if overlap:
                counter += 1
    if counter > MAX_OVERLAPS:
        raise ValidationError({'errors': [ErrorMessages.PS006.value]})


def check_overlapping_tyoskentelypaikka_object(validated_data, modelobj, *args):
    """
    Checks that the number of tyoskentelypaikka during any time period is less than the maximum
    """
    if args:
        model_id, original = get_model_id_and_original(modelobj, args[0])
    else:
        model_id, original = get_model_id_and_original(modelobj)

    palvelussuhde_id = validated_data['palvelussuhde'].id if 'palvelussuhde' in validated_data else original.palvelussuhde.id

    if original is not None:
        q_obj = Q(Q(palvelussuhde=palvelussuhde_id) & ~Q(pk=original.id))
    else:
        q_obj = Q(palvelussuhde=palvelussuhde_id)

    queryset = Tyoskentelypaikka.objects.filter(q_obj)

    alkamis_pvm, paattymis_pvm = get_alkamis_paattymis_pvm(validated_data, original)
    daterange_new = create_daterange(alkamis_pvm, paattymis_pvm)
    MAX_OVERLAPS = 3
    counter = 1
    for item in queryset:
        if item.id != int(model_id):
            daterange_existing = create_daterange(item.alkamis_pvm, item.paattymis_pvm)
            overlap = daterange_overlap(daterange_existing, daterange_new)
            if overlap:
                counter += 1
    if counter > MAX_OVERLAPS:
        raise ValidationError({'errors': [ErrorMessages.TA011.value]})


def check_overlapping_pidempipoissaolo_object(validated_data, modelobj, *args):
    """
    Checks that the number of pidempipoissaolo during any time period is less than the maximum
    """
    if args:
        model_id, original = get_model_id_and_original(modelobj, args[0])
    else:
        model_id, original = get_model_id_and_original(modelobj)

    palvelussuhde_id = validated_data['palvelussuhde'].id if 'palvelussuhde' in validated_data else original.palvelussuhde.id

    if original is not None:
        q_obj = Q(Q(palvelussuhde=palvelussuhde_id) & ~Q(pk=original.id))
    else:
        q_obj = Q(palvelussuhde=palvelussuhde_id)

    queryset = PidempiPoissaolo.objects.filter(q_obj)

    alkamis_pvm, paattymis_pvm = get_alkamis_paattymis_pvm(validated_data, original)
    daterange_new = create_daterange(alkamis_pvm, paattymis_pvm)
    MAX_OVERLAPS = 1
    counter = 1
    for item in queryset:
        if item.id != int(model_id):
            daterange_existing = create_daterange(item.alkamis_pvm, item.paattymis_pvm)
            overlap = daterange_overlap(daterange_existing, daterange_new)
            if overlap:
                counter += 1
    if counter > MAX_OVERLAPS:
        raise ValidationError({'palvelussuhde': [ErrorMessages.PP007.value]})


def get_model_id_and_original(modelobj, *args):
    if args:
        model_id = args[0]  # PUT/PATCH: changing existing object
        try:
            original = modelobj.objects.get(id=model_id)
        except modelobj.DoesNotExist:
            raise ValidationError({'errors': [ErrorMessages.GE016.value]})
    else:
        model_id = '0'  # POST: there is nothing existing for this object
        original = None
    return model_id, original


def get_alkamis_paattymis_pvm(data, original):
    alkamis_pvm = data['alkamis_pvm'] if 'alkamis_pvm' in data else original.alkamis_pvm
    if 'paattymis_pvm' in data:
        paattymis_pvm = data['paattymis_pvm']
    elif original:
        paattymis_pvm = original.paattymis_pvm
    else:
        paattymis_pvm = None
    return alkamis_pvm, paattymis_pvm


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
