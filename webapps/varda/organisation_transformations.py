import datetime

from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from guardian.models import UserObjectPermission
from rest_framework import serializers

from varda.cache import delete_cache_keys_related_model, delete_toimipaikan_lapset_cache
from varda.enums.ytj import YtjYritysmuoto
from varda.models import (Toimipaikka, VakaJarjestaja, PaosToiminta, Lapsi, Varhaiskasvatussuhde, Varhaiskasvatuspaatos,
                          Maksutieto, Huoltajuussuhde)
from varda.permission_groups import (assign_object_level_permissions, remove_object_level_permissions,
                                     get_permission_groups_for_organization)
from varda.permissions import (delete_object_permissions_explicitly, assign_lapsi_permissions,
                               assign_vakapaatos_vakasuhde_permissions, assign_maksutieto_permissions,
                               object_ids_organization_has_permissions_to)


PAOS_JARJESTAMISMUOTO_LIST = ['jm02', 'jm03']


def transfer_toimipaikat_to_vakajarjestaja(user, new_vakajarjestaja_id, toimipaikka_id_list):
    """
    Transfer toimipaikat to an existing organisaatio. End existing vakapaatokset, vakasuhteet, maksutiedot
    and start new ones.
    TODO: In the future also transfer henkilöstötiedot https://jira.eduuni.fi/browse/CSCVARDA-1749
    :param user: user object making the changes (needed for Model.changed_by)
    :param new_vakajarjestaja_id: ID of the vakajarjestaja that toimipaikat are transferred to
    :param toimipaikka_id_list: list of IDs of toimipaikat to be transferred
    :return:
    """

    today = datetime.date.today()

    # Check that new vakajarjestaja exists
    new_vakajarjestaja_obj = VakaJarjestaja.objects.filter(id=new_vakajarjestaja_id).first()
    if new_vakajarjestaja_obj is None:
        _raise_error('new_vakajarjestaja does not exist')

    # Get all toimipaikka objects that are transferred
    toimipaikka_list = Toimipaikka.objects.filter(id__in=toimipaikka_id_list)

    with transaction.atomic():
        for toimipaikka_obj in toimipaikka_list:
            old_vakajarjestaja_obj = toimipaikka_obj.vakajarjestaja

            if old_vakajarjestaja_obj == new_vakajarjestaja_obj:
                # Old and new vakajarjestaja are the same, raise error
                _raise_error('toimipaikka already belongs to new_vakajarjestaja')

            _raise_if_not_supported_transfer(old_vakajarjestaja_obj, new_vakajarjestaja_obj)

            if _toimipaikka_has_paos(toimipaikka_obj):
                _raise_error('toimipaikka has paos, transfer is not supported')

            """
            Remove permissions
            """
            # Disassociate all users from toimipaikka specific permission groups
            for group in get_permission_groups_for_organization(toimipaikka_obj.organisaatio_oid):
                group.user_set.clear()

            # Remove object level permissions from old vakajarjestaja permission groups
            remove_object_level_permissions(old_vakajarjestaja_obj.organisaatio_oid, Toimipaikka, toimipaikka_obj)

            # Remove user specific permissions explicitly
            UserObjectPermission.objects.filter(content_type=ContentType.objects.get_for_model(Toimipaikka),
                                                object_pk=toimipaikka_obj.id).delete()

            """
            Add permissions
            """
            # Add object level permisions to new vakajarjestaja permission groups
            assign_object_level_permissions(new_vakajarjestaja_obj.organisaatio_oid, Toimipaikka, toimipaikka_obj)

            """
            Handle lapsi, varhaiskasvatuspaatos, varhaiskasvatussuhde, and maksutieto permissions
            """
            lapsi_list = _get_toimipaikka_lapset(toimipaikka_obj)
            existing_lapsi_list = _get_vakajarjestaja_lapset_matching_lapsi_list(new_vakajarjestaja_obj, lapsi_list)

            # Handle lapsi permissions
            _transfer_lapsi_permissions_to_new_vakajarjestaja(user,
                                                              today,
                                                              new_vakajarjestaja_obj,
                                                              toimipaikka_obj,
                                                              lapsi_list,
                                                              existing_lapsi_list,
                                                              transfer_old=True)

            # Update toimipaikka.vakajarjestaja and save
            toimipaikka_obj.vakajarjestaja = new_vakajarjestaja_obj
            toimipaikka_obj.changed_by = user
            toimipaikka_obj.save()

            # Clear toimipaikka and old vakajarjestaja cache
            _delete_toimipaikka_cache(toimipaikka_obj.id)
            _delete_vakajarjestaja_cache(old_vakajarjestaja_obj.id)

        # Clear new vakajarjestaja cache
        _delete_vakajarjestaja_cache(new_vakajarjestaja_obj.id)


def merge_toimipaikka_to_other_toimipaikka(user, master_toimipaikka_id, old_toimipaikka_id):
    """
    Merge toimipaikka to an existing toimipaikka. Active information is transferred to new toimipaikka, but old
    toimipaikka retains historical information.
    TODO: In the future also transfer tyontekijat, tyoskentelypaikat
    :param user: user object making the changes (needed for Model.changed_by)
    :param master_toimipaikka_id: ID of the toimipaikka that receives vakatiedot from old_toimipaikka
    :param old_toimipaikka_id: ID of the toimipaikka that is to be merged to master_toimipaikka
    :return:
    """

    today = datetime.date.today()

    # Check master_toimipaikka is different from old_toimipaikka
    if master_toimipaikka_id == old_toimipaikka_id:
        raise serializers.ValidationError({'detail': ['master_toimipaikka and old_toimipaikka are the same object']})

    # Check master_toimipaikka exists
    master_toimipaikka_obj = Toimipaikka.objects.filter(id=master_toimipaikka_id).first()
    if master_toimipaikka_obj is None:
        raise serializers.ValidationError({'master_toimipaikka_id': ['master_toimipaikka does not exist']})

    # Check old toimipaikka exists
    old_toimipaikka_obj = Toimipaikka.objects.filter(id=old_toimipaikka_id).first()
    if old_toimipaikka_obj is None:
        raise serializers.ValidationError({'old_toimipaikka_id': ['old_toimipaikka does not exist']})

    master_vakajarjestaja_obj = master_toimipaikka_obj.vakajarjestaja
    old_vakajarjestaja_obj = old_toimipaikka_obj.vakajarjestaja

    _raise_if_not_supported_transfer(old_vakajarjestaja_obj, master_vakajarjestaja_obj)

    if _toimipaikka_has_paos(old_toimipaikka_obj):
        _raise_error('toimipaikka has paos, transfer is not supported')

    with transaction.atomic():
        lapsi_list = _get_toimipaikka_lapset(old_toimipaikka_obj)
        existing_lapsi_list = _get_vakajarjestaja_lapset_matching_lapsi_list(master_vakajarjestaja_obj, lapsi_list)

        # Handle lapsi permissions
        _transfer_lapsi_permissions_to_new_vakajarjestaja(user,
                                                          today,
                                                          master_vakajarjestaja_obj,
                                                          old_toimipaikka_obj,
                                                          lapsi_list,
                                                          existing_lapsi_list,
                                                          new_toimipaikka_obj=master_toimipaikka_obj)

        # Set old_toimipaikka inactive
        if old_toimipaikka_obj.paattymis_pvm is None or old_toimipaikka_obj.paattymis_pvm > today:
            old_toimipaikka_obj.paattymis_pvm = today
            old_toimipaikka_obj.save()

        # Clear old vakajarjestaja and toimipaikka cache
        _delete_toimipaikka_cache(old_toimipaikka_id)
        _delete_vakajarjestaja_cache(old_toimipaikka_obj.vakajarjestaja.id)

        # Clear master vakajarjestaja and toimipaikka cache
        _delete_toimipaikka_cache(master_toimipaikka_id)
        _delete_vakajarjestaja_cache(master_vakajarjestaja_obj.id)


def _transfer_lapsi_permissions_to_new_vakajarjestaja(user,
                                                      today,
                                                      new_vakajarjestaja_obj,
                                                      toimipaikka_obj,
                                                      lapsi_list,
                                                      existing_lapsi_list,
                                                      new_toimipaikka_obj=None,
                                                      transfer_old=False):
    """
    Parent method for transferring lapsi related data (lapsi, vakapaatos, vakasuhde, huoltajuussuhde, maksutieto)
    to new vakajarjestaja (and new toimipaikka)
    :param user: User object used in changed_by-fields
    :param today: current date object
    :param new_vakajarjestaja_obj: VakaJarjestaja object data is transferred to
    :param toimipaikka_obj: Toimipaikka object that is modified
    :param lapsi_list: QuerySet of Lapsi objects in toimipaikka
    :param existing_lapsi_list: QuerySet of Lapsi objects that belong to new_vakajarjestaja
    :param new_toimipaikka_obj: Toimipaikka object data is transferred to (additional)
    :param transfer_old: bool to signify if old data is transferred to new_vakajarjestaja or not
    :return:
    """
    for lapsi_obj in lapsi_list:
        new_lapsi_obj = _get_existing_lapsi_or_create_new(user, lapsi_obj.henkilo, existing_lapsi_list,
                                                          new_vakajarjestaja_obj, toimipaikka_obj)

        # Handle varhaiskasvatuspaatos permissions
        _transfer_vakapaatos_permissions_to_new_vakajarjestaja(user,
                                                               today,
                                                               new_vakajarjestaja_obj,
                                                               toimipaikka_obj,
                                                               lapsi_obj,
                                                               new_lapsi_obj,
                                                               new_toimipaikka_obj=new_toimipaikka_obj,
                                                               transfer_old=transfer_old)

        # Transfer all huoltajuussuhde objects to new lapsi
        _transfer_huoltajuussuhteet_to_new_lapsi(lapsi_obj, new_lapsi_obj)

        # Handle maksutieto permissions
        _transfer_maksutieto_permissions_to_new_vakajarjestaja(user,
                                                               today,
                                                               new_vakajarjestaja_obj,
                                                               toimipaikka_obj,
                                                               lapsi_obj,
                                                               new_lapsi_obj,
                                                               new_toimipaikka_obj=new_toimipaikka_obj,
                                                               transfer_old=transfer_old)

        if transfer_old:
            # Delete old huoltajuussuhteet, maksutiedot have been transferred
            Huoltajuussuhde.objects.filter(lapsi=lapsi_obj).delete()
            # Delete old lapsi object, everything has been transferred
            lapsi_obj.delete()


def _transfer_vakapaatos_permissions_to_new_vakajarjestaja(user,
                                                           today,
                                                           new_vakajarjestaja_obj,
                                                           toimipaikka_obj,
                                                           lapsi_obj,
                                                           new_lapsi_obj,
                                                           new_toimipaikka_obj=None,
                                                           transfer_old=False):
    for vakapaatos_obj in lapsi_obj.varhaiskasvatuspaatokset.all():
        # End all valid vakapaatokset and create new ones so that toimipaikka owner change is reported correctly
        new_vakapaatos_obj = None
        if vakapaatos_obj.paattymis_pvm is None or vakapaatos_obj.paattymis_pvm > today:
            # Create new vakapaatos if vakapaatos has active vakasuhde in toimipaikka
            vakasuhde_filter = Q(toimipaikka=toimipaikka_obj) & (Q(paattymis_pvm=None) | Q(paattymis_pvm__gt=today))
            if vakapaatos_obj.varhaiskasvatussuhteet.filter(vakasuhde_filter).exists():
                new_vakapaatos_obj = (Varhaiskasvatuspaatos
                                      .objects
                                      .create(lapsi=new_lapsi_obj,
                                              vuorohoito_kytkin=vakapaatos_obj.vuorohoito_kytkin,
                                              pikakasittely_kytkin=vakapaatos_obj.pikakasittely_kytkin,
                                              tuntimaara_viikossa=vakapaatos_obj.tuntimaara_viikossa,
                                              paivittainen_vaka_kytkin=vakapaatos_obj.paivittainen_vaka_kytkin,
                                              kokopaivainen_vaka_kytkin=vakapaatos_obj.kokopaivainen_vaka_kytkin,
                                              jarjestamismuoto_koodi=vakapaatos_obj.jarjestamismuoto_koodi,
                                              hakemus_pvm=vakapaatos_obj.hakemus_pvm,
                                              alkamis_pvm=today,
                                              paattymis_pvm=vakapaatos_obj.paattymis_pvm,
                                              changed_by=user))

                vakapaatos_toimipaikka_obj = toimipaikka_obj if not new_toimipaikka_obj else new_toimipaikka_obj

                # Assign new vakapaatos permissions to new vakajarjestaja and to toimipaikka
                assign_vakapaatos_vakasuhde_permissions(Varhaiskasvatuspaatos,
                                                        new_vakajarjestaja_obj.organisaatio_oid,
                                                        vakapaatos_toimipaikka_obj.organisaatio_oid,
                                                        new_vakapaatos_obj)

            # End old vakapaatos
            vakapaatos_obj.paattymis_pvm = today
            vakapaatos_obj.changed_by = user
            vakapaatos_obj.save()

        if transfer_old:
            # Remove user and group specific permissions explicitly
            delete_object_permissions_explicitly(Varhaiskasvatuspaatos, vakapaatos_obj.id)
            # Assign permissions to new vakajarjestaja and again to toimipaikka
            assign_vakapaatos_vakasuhde_permissions(Varhaiskasvatuspaatos,
                                                    new_vakajarjestaja_obj.organisaatio_oid,
                                                    toimipaikka_obj.organisaatio_oid,
                                                    vakapaatos_obj)
            # Transfer vakapaatos to new lapsi object
            vakapaatos_obj.lapsi = new_lapsi_obj
            vakapaatos_obj.changed_by = user
            # Save changes (lapsi and possible paattymis_pvm)
            vakapaatos_obj.save()

        # Handle varhaiskasvatussuhde permissions
        _transfer_vakasuhde_permissions_to_new_vakajarjestaja(user,
                                                              today,
                                                              new_vakajarjestaja_obj,
                                                              toimipaikka_obj,
                                                              vakapaatos_obj,
                                                              new_vakapaatos_obj=new_vakapaatos_obj,
                                                              new_toimipaikka_obj=new_toimipaikka_obj,
                                                              transfer_old=transfer_old)

        # Clear vakapaatos cache
        delete_cache_keys_related_model('varhaiskasvatuspaatos', vakapaatos_obj.id)


def _transfer_vakasuhde_permissions_to_new_vakajarjestaja(user,
                                                          today,
                                                          new_vakajarjestaja_obj,
                                                          toimipaikka_obj,
                                                          vakapaatos_obj,
                                                          new_vakapaatos_obj=None,
                                                          new_toimipaikka_obj=None,
                                                          transfer_old=False):
    for vakasuhde_obj in vakapaatos_obj.varhaiskasvatussuhteet.all():
        if transfer_old:
            # Remove user and group specific permissions explicitly
            delete_object_permissions_explicitly(Varhaiskasvatussuhde, vakasuhde_obj.id)
            # Assign permissions to new vakajarjestaja and again to toimipaikka
            assign_vakapaatos_vakasuhde_permissions(Varhaiskasvatussuhde,
                                                    new_vakajarjestaja_obj.organisaatio_oid,
                                                    toimipaikka_obj.organisaatio_oid,
                                                    vakasuhde_obj)

        # Check if vakasuhde is active and linked to different toimipaikka
        if (vakasuhde_obj.toimipaikka.id != toimipaikka_obj.id and
                (vakasuhde_obj.paattymis_pvm is None or vakasuhde_obj.paattymis_pvm > today)):
            # End vakasuhde, old vakajarjestaja has to create new vakapaatos and vakasuhde
            vakasuhde_obj.paattymis_pvm = today
            vakasuhde_obj.changed_by = user
            vakasuhde_obj.save()

        # Check if new vakapaatos was created and vakasuhde is still valid
        if new_vakapaatos_obj and (vakasuhde_obj.paattymis_pvm is None or vakasuhde_obj.paattymis_pvm > today):
            # Create new_vakasuhde to new_toimipaikka if it was provided
            vakasuhde_toimipaikka_obj = toimipaikka_obj if not new_toimipaikka_obj else new_toimipaikka_obj

            # Create new vakasuhde
            new_vakasuhde_obj = (Varhaiskasvatussuhde
                                 .objects
                                 .create(toimipaikka=vakasuhde_toimipaikka_obj,
                                         varhaiskasvatuspaatos=new_vakapaatos_obj,
                                         alkamis_pvm=today,
                                         paattymis_pvm=vakasuhde_obj.paattymis_pvm,
                                         changed_by=user))

            # Assign new vakasuhde permissions to new vakajarjestaja and to toimipaikka
            assign_vakapaatos_vakasuhde_permissions(Varhaiskasvatussuhde,
                                                    new_vakajarjestaja_obj.organisaatio_oid,
                                                    vakasuhde_toimipaikka_obj.organisaatio_oid,
                                                    new_vakasuhde_obj)

            # End old vakasuhde
            vakasuhde_obj.paattymis_pvm = today
            vakasuhde_obj.changed_by = user
            vakasuhde_obj.save()


def _transfer_huoltajuussuhteet_to_new_lapsi(lapsi_obj, new_lapsi_obj):
    for huoltajuussuhde_obj in lapsi_obj.huoltajuussuhteet.all():
        # Create new huoltajuussuhde in case new_lapsi doesn't already have it
        new_huoltajuussuhde_obj = (Huoltajuussuhde
                                   .objects
                                   .get_or_create(lapsi=new_lapsi_obj,
                                                  huoltaja=huoltajuussuhde_obj.huoltaja,
                                                  defaults={'voimassa_kytkin': huoltajuussuhde_obj.voimassa_kytkin,
                                                            'changed_by': new_lapsi_obj.changed_by}))

        # Set voimassa_kytkin True if other huoltajuussuhde was active
        if not new_huoltajuussuhde_obj[0].voimassa_kytkin and huoltajuussuhde_obj.voimassa_kytkin:
            new_huoltajuussuhde_obj.voimassa_kytkin = True
            new_huoltajuussuhde_obj.save()


def _transfer_maksutieto_permissions_to_new_vakajarjestaja(user,
                                                           today,
                                                           new_vakajarjestaja_obj,
                                                           toimipaikka_obj,
                                                           lapsi_obj,
                                                           new_lapsi_obj,
                                                           new_toimipaikka_obj=None,
                                                           transfer_old=False):
    for maksutieto_obj in Maksutieto.objects.filter(huoltajuussuhteet__lapsi=lapsi_obj).distinct():
        if transfer_old:
            # Remove user and group specific permissions explicitly
            delete_object_permissions_explicitly(Maksutieto, maksutieto_obj.id)
            # Assign permissions to new vakajarjestaja and again to toimipaikka
            assign_maksutieto_permissions(new_vakajarjestaja_obj.organisaatio_oid, toimipaikka_obj, maksutieto_obj)

        # Check if maksutieto is still valid
        # End all valid maksutiedot and create new ones so that toimipaikka change is reported correctly
        new_maksutieto_obj = None
        if maksutieto_obj.paattymis_pvm is None or maksutieto_obj.paattymis_pvm > today:
            # Create new maksutieto
            new_maksutieto_obj = (Maksutieto
                                  .objects
                                  .create(yksityinen_jarjestaja=False,
                                          maksun_peruste_koodi=maksutieto_obj.maksun_peruste_koodi,
                                          palveluseteli_arvo=maksutieto_obj.palveluseteli_arvo,
                                          asiakasmaksu=maksutieto_obj.asiakasmaksu,
                                          perheen_koko=maksutieto_obj.perheen_koko,
                                          alkamis_pvm=today,
                                          paattymis_pvm=maksutieto_obj.paattymis_pvm,
                                          changed_by=user))

            maksutieto_toimipaikka_obj = toimipaikka_obj if not new_toimipaikka_obj else new_toimipaikka_obj
            # Assign new maksutieto permissions to new vakajarjestaja and to toimipaikka
            assign_maksutieto_permissions(new_vakajarjestaja_obj.organisaatio_oid,
                                          maksutieto_toimipaikka_obj,
                                          new_maksutieto_obj)

            # End old maksutieto
            maksutieto_obj.paattymis_pvm = today
            maksutieto_obj.changed_by = user
            maksutieto_obj.save()

        # Add maksutieto (and new_maksutieto) to huoltajuussuhteet under new_lapsi
        for huoltajuussuhde_obj in maksutieto_obj.huoltajuussuhteet.all():
            maksutieto_id_list = []
            if transfer_old:
                maksutieto_id_list.append(maksutieto_obj.id)
            if new_maksutieto_obj:
                maksutieto_id_list.append(new_maksutieto_obj.id)

            Huoltajuussuhde.objects.get(lapsi=new_lapsi_obj,
                                        huoltaja=huoltajuussuhde_obj.huoltaja).maksutiedot.add(*maksutieto_id_list)


def _vakajarjestaja_is_yksityinen(vakajarjestaja):
    return vakajarjestaja.yritysmuoto not in [YtjYritysmuoto.KUNTA.name, YtjYritysmuoto.KUNTAYHTYMA.name]


def _raise_if_not_supported_transfer(old_vakajarjestaja, new_vakajarjestaja):
    """
    Only yksityinen -> yksityinen and kunnallinen -> kunnallinen transfers are supported
    :param old_vakajarjestaja: VakaJarjestaja object 1
    :param new_vakajarjestaja: VakaJarjestaja object 2
    :return:
    """
    old_is_yksityinen = _vakajarjestaja_is_yksityinen(old_vakajarjestaja)
    new_is_yksityinen = _vakajarjestaja_is_yksityinen(new_vakajarjestaja)

    if not old_is_yksityinen == new_is_yksityinen:
        _raise_error('only yksityinen->yksityinen and kunnallinen->kunnallinen transfers are supported')


def _get_toimipaikka_lapset(toimipaikka):
    """
    Get lapset with vakasuhde in this toimipaikka
    :param toimipaikka: Toimipaikka object
    :return: QuerySet of Lapsi objects that have vakasuhde in toimipaikka
    """

    # There might be lapsi that have old vakasuhde in this toimipaikka but belong to some other vakajarjestaja
    # We do not want to transfer those, so get only lapset toimipaikka.vakajarjestaja has permissions to
    vakajarjestaja_lapsi_id_list = object_ids_organization_has_permissions_to(toimipaikka.vakajarjestaja.organisaatio_oid, Lapsi)
    return Lapsi.objects.filter(id__in=vakajarjestaja_lapsi_id_list,
                                varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka=toimipaikka,
                                paos_organisaatio=None).distinct()


def _toimipaikka_has_paos(toimipaikka):
    """
    Determine if Toimipaikka has paos-toiminta
    :param toimipaikka: Toimipaikka object
    :return: boolean
    """
    # Check if paos-jarjestamismuoto is listed in toimipaikka.jarjestamismuodot
    if any(koodi in PAOS_JARJESTAMISMUOTO_LIST for koodi in toimipaikka.jarjestamismuoto_koodi):
        return True

    # Check if toimipaikka is linked to PaosToiminta
    paos_toiminta_qs = PaosToiminta.objects.filter(paos_toimipaikka=toimipaikka)
    # Check if there are any vakapaatos with paos-jarjestamismuoto
    vakapaatos_qs = Varhaiskasvatuspaatos.objects.filter(jarjestamismuoto_koodi__in=PAOS_JARJESTAMISMUOTO_LIST,
                                                         varhaiskasvatussuhteet__toimipaikka=toimipaikka)
    # Check if there are lapsi with paos_organisaatio
    lapsi_qs = Lapsi.objects.filter(Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka=toimipaikka) &
                                    ~Q(paos_organisaatio=None))

    return paos_toiminta_qs.exists() or vakapaatos_qs.exists() or lapsi_qs.exists()


def _get_vakajarjestaja_lapset_matching_lapsi_list(vakajarjestaja, lapsi_list):
    """
    Get lapset of vakajarjestaja that reference same henkilot as lapset in lapsi_list
    Only get lapset that vakajarjestaja has permissions to and who are not paos-lapsi
    :param vakajarjestaja: VakaJarjestaja object
    :param lapsi_list: QuerySet of Lapsi objects that are used in matching
    :return: QuerySet of Lapsi objects that belong to vakajarjestaja and match lapsi_list
    """

    henkilo_id_list = lapsi_list.values_list('henkilo', flat=True)
    new_vakajarjestaja_lapsi_id_list = object_ids_organization_has_permissions_to(vakajarjestaja.organisaatio_oid,
                                                                                  Lapsi)
    return (Lapsi.objects
            .filter(Q(id__in=new_vakajarjestaja_lapsi_id_list) & Q(henkilo__in=henkilo_id_list) &
                    (Q(vakatoimija=vakajarjestaja) |
                     (Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__vakajarjestaja=vakajarjestaja) &
                      Q(paos_organisaatio=None)))))


def _get_existing_lapsi_or_create_new(user, henkilo, lapsi_list, vakajarjestaja, toimipaikka):
    """
    If vakajarjestaja already has a lapsi that references henkilo, we don't want to create a new one
    because vakajarjestaja can have only one lapsi referencing speficic henkilo. Vakatiedot are transferred to
    that lapsi. If no such lapsi exists, it is created, with permissions to vakajarjestaja and toimipaikka
    :param user: User object (used in changed_by-field)
    :param henkilo: Henkilo object used in matching
    :param lapsi_list: QuerySet of Lapsi objects used in matching
    :param vakajarjestaja: VakaJarjestaja object lapsi belongs to
    :param toimipaikka: Toimipaikka object lapsi belongs to
    :return: new or existing Lapsi object
    """
    colliding_lapsi = lapsi_list.filter(henkilo=henkilo)
    if colliding_lapsi.exists():
        lapsi = colliding_lapsi.first()
    else:
        # Create new Lapsi object
        lapsi = Lapsi.objects.create(henkilo=henkilo, vakatoimija=vakajarjestaja, changed_by=user)

        # Assign permissions to vakajarjestaja
        assign_lapsi_permissions(vakajarjestaja.organisaatio_oid, lapsi)

    # Assign permissions to toimipaikka
    if toimipaikka.organisaatio_oid != '':
        assign_lapsi_permissions(toimipaikka.organisaatio_oid, lapsi)

    return lapsi


def _delete_toimipaikka_cache(toimipaikka_id):
    delete_cache_keys_related_model('toimipaikka', toimipaikka_id)
    delete_toimipaikan_lapset_cache(str(toimipaikka_id))


def _delete_vakajarjestaja_cache(vakajarjestaja_id):
    delete_cache_keys_related_model('vakajarjestaja', vakajarjestaja_id)
    cache.delete('vakajarjestaja_yhteenveto_' + str(vakajarjestaja_id))


def _raise_error(msg):
    raise serializers.ValidationError({'detail': [msg]})
