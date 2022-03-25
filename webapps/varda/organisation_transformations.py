from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from rest_framework import serializers

from varda.misc import flatten_nested_list
from varda.models import (Toimipaikka, Lapsi, Varhaiskasvatussuhde, Varhaiskasvatuspaatos, Maksutieto, Huoltajuussuhde,
                          Tyontekija, Tutkinto, Taydennyskoulutus, TaydennyskoulutusTyontekija, Palvelussuhde,
                          Tyoskentelypaikka, PidempiPoissaolo, TilapainenHenkilosto, MaksutietoHuoltajuussuhde)
from varda.permission_groups import (get_all_permission_groups_for_organization, assign_permissions_for_toimipaikka,
                                     assign_object_permissions_to_all_henkilosto_groups,
                                     assign_object_permissions_to_taydennyskoulutus_groups,
                                     assign_object_permissions_to_tyontekija_groups,
                                     assign_object_permissions_to_tilapainenhenkilosto_groups)
from varda.permissions import (delete_object_permissions_explicitly, assign_object_level_permissions_for_instance,
                               assign_maksutieto_permissions, assign_lapsi_henkilo_permissions,
                               delete_permissions_from_object_instance_by_oid, assign_tyontekija_henkilo_permissions,
                               get_tyontekija_and_toimipaikka_lists_for_taydennyskoulutus)


def transfer_toimipaikat_to_vakajarjestaja(new_vakajarjestaja, old_vakajarjestaja):
    """
    Transfer all Toimipaikka objects from old_vakajarjestaja to new_vakajarjestaja.
    :param new_vakajarjestaja: Organisaatio object to which Toimipaikka objects are transferred
    :param old_vakajarjestaja: Organisaatio object from which Toimipaikka objects are transferred
    """
    _verify_transfer_is_supported(new_vakajarjestaja, old_vakajarjestaja)
    with transaction.atomic():
        # Handle Lapsi object permissions
        _transfer_lapsi_permissions_to_new_vakajarjestaja(new_vakajarjestaja, old_vakajarjestaja)

        # Handle Tyontekija object permissions
        _transfer_tyontekija_permissions_to_new_vakajarjestaja(new_vakajarjestaja, old_vakajarjestaja)

        # Handle Toimipaikka transfer
        _transfer_toimipaikka_permissions_to_new_vakajarjestaja(new_vakajarjestaja, old_vakajarjestaja)

        # Clear cache
        cache.clear()


def _verify_transfer_is_supported(new_vakajarjestaja, old_vakajarjestaja):
    # Check that new_vakajarjestaja and old_vakajarjestaja are different
    if new_vakajarjestaja == old_vakajarjestaja:
        _raise_error('new_vakajarjestaja and old_vakajarjestaja cannot be the same')

    # Check that transfer is kunta -> kunta or yksityinen -> yksityinen
    if new_vakajarjestaja.kunnallinen_kytkin != old_vakajarjestaja.kunnallinen_kytkin:
        _raise_error('only kunta -> kunta and yksityinen -> yksityinen transfers are supported')

    # Check that old_vakajarjestaja does not have PAOS Lapsi objects
    if Lapsi.objects.filter(paos_organisaatio=old_vakajarjestaja).exists():
        _raise_error('old_vakajarjestaja has PAOS Lapsi objects in its Toimipaikka objects')


def _transfer_toimipaikka_permissions_to_new_vakajarjestaja(new_vakajarjestaja, old_vakajarjestaja):
    toimipaikka_id_list = old_vakajarjestaja.toimipaikat.values_list('id', flat=True)
    toimipaikka_qs = Toimipaikka.objects.filter(id__in=toimipaikka_id_list)

    for toimipaikka in toimipaikka_qs:
        # Disassociate all users from Toimipaikka specific permission groups
        for group in get_all_permission_groups_for_organization(toimipaikka.organisaatio_oid):
            group.user_set.clear()

        # Delete permissions
        delete_object_permissions_explicitly(Toimipaikka, toimipaikka.id)

        # Change Organisaatio reference of Toimipaikka
        toimipaikka.vakajarjestaja = new_vakajarjestaja
        toimipaikka.save()

        # Assign permissions
        assign_permissions_for_toimipaikka(toimipaikka, new_vakajarjestaja.organisaatio_oid)

        _transfer_painotus_permissions_to_new_vakajarjestaja(new_vakajarjestaja, toimipaikka)


def _transfer_painotus_permissions_to_new_vakajarjestaja(new_vakajarjestaja, toimipaikka):
    toiminnallinen_painotus_qs = toimipaikka.toiminnallisetpainotukset.all()
    kielipainotus_qs = toimipaikka.kielipainotukset.all()
    for painotus in (*toiminnallinen_painotus_qs, *kielipainotus_qs,):
        # Delete permissions
        delete_object_permissions_explicitly(type(painotus), painotus.id)

        # Assign permissions
        assign_object_level_permissions_for_instance(painotus, (new_vakajarjestaja.organisaatio_oid,
                                                                toimipaikka.organisaatio_oid,))


def _get_vakajarjestaja_lapset_qs(vakajarjestaja):
    return Lapsi.objects.filter(Q(vakatoimija=vakajarjestaja) |
                                (Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__vakajarjestaja=vakajarjestaja) &
                                 Q(paos_organisaatio=None))).distinct('id')


def _transfer_lapsi_permissions_to_new_vakajarjestaja(new_vakajarjestaja, old_vakajarjestaja):
    """
    Parent method for transferring Lapsi related permissions (Lapsi, Varhaiskasvatuspaatos, Varhaiskasvatussuhde,
    Huoltajuussuhde, Maksutieto) to new Organisaatio
    :param new_vakajarjestaja: Organisaatio object which Lapsi related data is transferred to
    :param old_vakajarjestaja: Organisaatio object which Lapsi related data is transferred from
    """
    lapsi_qs = _get_vakajarjestaja_lapset_qs(old_vakajarjestaja)
    existing_lapsi_qs = _get_vakajarjestaja_lapset_qs(new_vakajarjestaja)
    for lapsi in lapsi_qs:
        toimipaikka_oid_set = set(lapsi.varhaiskasvatuspaatokset
                                  .values_list('varhaiskasvatussuhteet__toimipaikka__organisaatio_oid', flat=True))

        # Check if new_vakajarjestaja already has same Lapsi object
        existing_lapsi = None
        if existing_lapsi_obj := existing_lapsi_qs.filter(henkilo=lapsi.henkilo).first():
            existing_lapsi = existing_lapsi_obj
            # Add toimipaikka_oids of existing Lapsi to the set
            toimipaikka_oid_set |= set(existing_lapsi.varhaiskasvatuspaatokset
                                       .values_list('varhaiskasvatussuhteet__toimipaikka__organisaatio_oid', flat=True))

        if not existing_lapsi:
            # Change vakatoimija of Lapsi object
            lapsi.vakatoimija = new_vakajarjestaja
            lapsi.save()

            # Delete Henkilo permissions, only from old_vakajarjestaja, if old_vakajarjestaja does not have PAOS-lapsi
            # that remains
            if not Lapsi.objects.filter(oma_organisaatio=old_vakajarjestaja, henkilo=lapsi.henkilo).exists():
                delete_permissions_from_object_instance_by_oid(lapsi.henkilo, old_vakajarjestaja.organisaatio_oid)

            # Assign Henkilo permissions, only for new_vakajarjestaja
            assign_lapsi_henkilo_permissions(lapsi)

            # Delete Lapsi permissions
            delete_object_permissions_explicitly(Lapsi, lapsi.id)

            # Assign Lapsi permissions
            assign_object_level_permissions_for_instance(lapsi, (new_vakajarjestaja.organisaatio_oid,
                                                                 toimipaikka_oid_set))

        _transfer_vakapaatos_permissions_to_new_vakajarjestaja(new_vakajarjestaja, lapsi, existing_lapsi=existing_lapsi)
        _transfer_maksutieto_permissions_to_new_vakajarjestaja(new_vakajarjestaja, toimipaikka_oid_set, lapsi,
                                                               existing_lapsi=existing_lapsi)

        if existing_lapsi:
            # Lapsi related data was transferred to an existing Lapsi object, so delete the old one
            MaksutietoHuoltajuussuhde.objects.filter(huoltajuussuhde__lapsi=lapsi).delete()
            Huoltajuussuhde.objects.filter(lapsi=lapsi).delete()
            lapsi.delete()


def _transfer_vakapaatos_permissions_to_new_vakajarjestaja(new_vakajarjestaja, lapsi, existing_lapsi=None):
    for vakapaatos in lapsi.varhaiskasvatuspaatokset.all():
        # Delete permissions
        delete_object_permissions_explicitly(Varhaiskasvatuspaatos, vakapaatos.id)

        # Assign permissions
        toimipaikka_oid_set = set(vakapaatos.varhaiskasvatussuhteet
                                  .values_list('toimipaikka__organisaatio_oid', flat=True))
        assign_object_level_permissions_for_instance(vakapaatos, (new_vakajarjestaja.organisaatio_oid,
                                                                  toimipaikka_oid_set,))

        if existing_lapsi:
            # Transfer vakapaatos to existing lapsi
            vakapaatos.lapsi = existing_lapsi
            vakapaatos.save()

        _transfer_vakasuhde_permissions_to_new_vakajarjestaja(new_vakajarjestaja, vakapaatos)


def _transfer_vakasuhde_permissions_to_new_vakajarjestaja(new_vakajarjestaja, vakapaatos):
    for vakasuhde in vakapaatos.varhaiskasvatussuhteet.all():
        # Delete permissions
        delete_object_permissions_explicitly(Varhaiskasvatussuhde, vakasuhde.id)

        # Assign permissions
        assign_object_level_permissions_for_instance(vakasuhde, (new_vakajarjestaja.organisaatio_oid,
                                                                 vakasuhde.toimipaikka.organisaatio_oid,))


def _transfer_maksutieto_permissions_to_new_vakajarjestaja(new_vakajarjestaja, toimipaikka_oid_set, lapsi,
                                                           existing_lapsi=None):
    for maksutieto in Maksutieto.objects.filter(huoltajuussuhteet__lapsi=lapsi).distinct():
        # Delete permissions
        delete_object_permissions_explicitly(Maksutieto, maksutieto.id)

        # Assign permissions
        assign_maksutieto_permissions(new_vakajarjestaja.organisaatio_oid, maksutieto,
                                      toimipaikka_oid_list=toimipaikka_oid_set)

        if existing_lapsi:
            # Transfer Maksutieto object for existing Lapsi object
            for maksutieto_huoltajuussuhde in maksutieto.maksutiedot_huoltajuussuhteet.all():
                huoltajuussuhde = Huoltajuussuhde.objects.get(lapsi=existing_lapsi,
                                                              huoltaja=maksutieto_huoltajuussuhde.huoltajuussuhde.huoltaja)
                MaksutietoHuoltajuussuhde.objects.create(huoltajuussuhde=huoltajuussuhde, maksutieto=maksutieto,
                                                         changed_by=maksutieto_huoltajuussuhde.changed_by)

        # Save Maksutieto without modifications so that new historical record is created
        maksutieto.save()


def _transfer_tyontekija_permissions_to_new_vakajarjestaja(new_vakajarjestaja, old_vakajarjestaja):
    """
    Parent method for transferring Tyontekija related permissions (Tyontekija, Tutkinto, Palvelussuhde,
    Tyoskentelypaikka, PidempiPoissaolo, Taydennyskoulutus) and TilapainenHenkilosto to new Organisaatio
    :param new_vakajarjestaja: Organisaatio object which Tyontekija related data is transferred to
    :param old_vakajarjestaja: Organisaatio object which Tyontekija related data is transferred from
    """
    _transfer_tilapainen_henkilosto_permissions_to_new_vakajarjestaja(new_vakajarjestaja, old_vakajarjestaja)
    _transfer_taydennyskoulutus_permissions_to_new_vakajarjestaja(new_vakajarjestaja, old_vakajarjestaja)
    _transfer_tutkinto_permissions_to_new_vakajarjestaja(new_vakajarjestaja, old_vakajarjestaja)

    tyontekija_qs = Tyontekija.objects.filter(vakajarjestaja=old_vakajarjestaja)
    existing_tyontekija_qs = Tyontekija.objects.filter(vakajarjestaja=new_vakajarjestaja)
    for tyontekija in tyontekija_qs:
        tyontekija_oid_set = _get_tyontekija_oid_set(new_vakajarjestaja, tyontekija)

        # Check if new_vakajarjestaja already has same Tyontekija object
        existing_tyontekija = None
        if existing_tyontekija_obj := existing_tyontekija_qs.filter(henkilo=tyontekija.henkilo).first():
            existing_tyontekija = existing_tyontekija_obj

        if not existing_tyontekija:
            # Change vakajarjestaja of Tyontekija object
            tyontekija.vakajarjestaja = new_vakajarjestaja
            tyontekija.save()

            # Delete Henkilo permissions, only from old_vakajarjestaja
            delete_permissions_from_object_instance_by_oid(tyontekija.henkilo, old_vakajarjestaja.organisaatio_oid)

            # Assign Henkilo permissions, only for new_vakajarjestaja
            assign_tyontekija_henkilo_permissions(tyontekija)

            # Delete Tyontekija permissions
            delete_object_permissions_explicitly(Tyontekija, tyontekija.id)

            # Assign Tyontekija permissions
            for organisaatio_oid in tyontekija_oid_set:
                if organisaatio_oid:
                    assign_object_permissions_to_all_henkilosto_groups(organisaatio_oid, Tyontekija, tyontekija)

        _transfer_palvelussuhde_permissions_to_new_vakajarjestaja(new_vakajarjestaja, tyontekija,
                                                                  existing_tyontekija=existing_tyontekija)

        if existing_tyontekija:
            # Tyontekija related data was transferred to an existing Tyontekija object, so delete the old one
            tyontekija.delete()


def _transfer_tilapainen_henkilosto_permissions_to_new_vakajarjestaja(new_vakajarjestaja, old_vakajarjestaja):
    for tilapainen_henkilosto in TilapainenHenkilosto.objects.filter(vakajarjestaja=old_vakajarjestaja):
        existing_tilapainen_henkilosto = (TilapainenHenkilosto.objects
                                          .filter(vakajarjestaja=new_vakajarjestaja,
                                                  kuukausi__month=tilapainen_henkilosto.kuukausi.month,
                                                  kuukausi__year=tilapainen_henkilosto.kuukausi.year)
                                          .first())
        if existing_tilapainen_henkilosto:
            # new_vakajarjestaja already has TilapainenHenkilosto object for this month
            existing_tilapainen_henkilosto.tuntimaara += tilapainen_henkilosto.tuntimaara
            existing_tilapainen_henkilosto.tyontekijamaara += tilapainen_henkilosto.tyontekijamaara
            existing_tilapainen_henkilosto.save()
            # Delete old TilapainenHenkilosto object
            tilapainen_henkilosto.delete()
        else:
            # new_vakajarjestaja does not have TilapainenHenkilosto object for this month so object can be
            # transferred
            delete_object_permissions_explicitly(TilapainenHenkilosto, tilapainen_henkilosto.id)
            assign_object_permissions_to_tilapainenhenkilosto_groups(new_vakajarjestaja.organisaatio_oid,
                                                                     TilapainenHenkilosto, tilapainen_henkilosto)
            tilapainen_henkilosto.vakajarjestaja = new_vakajarjestaja
            tilapainen_henkilosto.save()


def _transfer_tutkinto_permissions_to_new_vakajarjestaja(new_vakajarjestaja, old_vakajarjestaja):
    for tutkinto in Tutkinto.objects.filter(vakajarjestaja=old_vakajarjestaja):
        if Tutkinto.objects.filter(vakajarjestaja=new_vakajarjestaja, henkilo=tutkinto.henkilo,
                                   tutkinto_koodi=tutkinto.tutkinto_koodi).exists():
            # If new_vakajarjestaja already has duplicate Tutkinto object, delete the old one
            tutkinto.delete()
        else:
            # new_vakajarjestaja does not yet have a similar Tutkinto object
            # Delete permissions
            delete_object_permissions_explicitly(Tutkinto, tutkinto.id)

            # Assign permissions
            tyontekija = Tyontekija.objects.get(vakajarjestaja=old_vakajarjestaja, henkilo=tutkinto.henkilo)
            tyontekija_oid_set = _get_tyontekija_oid_set(new_vakajarjestaja, tyontekija)
            for organisaatio_oid in tyontekija_oid_set:
                if organisaatio_oid:
                    assign_object_permissions_to_tyontekija_groups(organisaatio_oid, Tutkinto, tutkinto)

            # Update vakajarjestaja field
            tutkinto.vakajarjestaja = new_vakajarjestaja
            tutkinto.save()


def _transfer_palvelussuhde_permissions_to_new_vakajarjestaja(new_vakajarjestaja, tyontekija, existing_tyontekija=None):
    for palvelussuhde in tyontekija.palvelussuhteet.all():
        # Delete permissions
        delete_object_permissions_explicitly(Palvelussuhde, palvelussuhde.id)

        # Assign permissions
        palvelussuhde_oid_set = set(palvelussuhde.tyoskentelypaikat.all()
                                    .values_list('toimipaikka__organisaatio_oid', flat=True))
        palvelussuhde_oid_set.add(new_vakajarjestaja.organisaatio_oid)
        palvelussuhde_oid_set.discard(None)
        for organisaatio_oid in palvelussuhde_oid_set:
            if organisaatio_oid:
                assign_object_permissions_to_all_henkilosto_groups(organisaatio_oid, Palvelussuhde, palvelussuhde)

        if existing_tyontekija:
            # Transfer Palvelussuhde to existing Tyontekija
            palvelussuhde.tyontekija = existing_tyontekija
            palvelussuhde.save()

        _transfer_tyoskentelypaikka_permissions_to_new_vakajarjestaja(new_vakajarjestaja, palvelussuhde)
        _transfer_pidempi_poissaolo_permissions_to_new_vakajarjestaja(palvelussuhde_oid_set, palvelussuhde)


def _transfer_tyoskentelypaikka_permissions_to_new_vakajarjestaja(new_vakajarjestaja, palvelussuhde):
    for tyoskentelypaikka in palvelussuhde.tyoskentelypaikat.all():
        # Delete permissions
        delete_object_permissions_explicitly(Tyoskentelypaikka, tyoskentelypaikka.id)

        # Assign permissions
        for organisaatio_oid in (new_vakajarjestaja.organisaatio_oid, tyoskentelypaikka.toimipaikka.organisaatio_oid,):
            if organisaatio_oid:
                assign_object_permissions_to_tyontekija_groups(organisaatio_oid, Tyoskentelypaikka, tyoskentelypaikka)


def _transfer_pidempi_poissaolo_permissions_to_new_vakajarjestaja(palvelussuhde_oid_set, palvelussuhde):
    for pidempi_poissaolo in palvelussuhde.pidemmatpoissaolot.all():
        # Delete permissions
        delete_object_permissions_explicitly(PidempiPoissaolo, pidempi_poissaolo.id)

        for organisaatio_oid in palvelussuhde_oid_set:
            if organisaatio_oid:
                assign_object_permissions_to_tyontekija_groups(organisaatio_oid, PidempiPoissaolo, pidempi_poissaolo)


def _transfer_taydennyskoulutus_permissions_to_new_vakajarjestaja(new_vakajarjestaja, old_vakajarjestaja):
    existing_tyontekija_qs = Tyontekija.objects.filter(vakajarjestaja=new_vakajarjestaja)

    for taydennyskoulutus in (Taydennyskoulutus.objects.filter(tyontekijat__vakajarjestaja=old_vakajarjestaja).distinct()):
        # Delete permissions
        delete_object_permissions_explicitly(Taydennyskoulutus, taydennyskoulutus.id)

        tyontekija_id_list, toimipaikka_oid_list_list_original = get_tyontekija_and_toimipaikka_lists_for_taydennyskoulutus(
            taydennyskoulutus.taydennyskoulutukset_tyontekijat.all()
        )
        taydennyskoulutus_oid_set = set(flatten_nested_list(toimipaikka_oid_list_list_original))
        taydennyskoulutus_oid_set.add(new_vakajarjestaja.organisaatio_oid)

        for taydennyskoulutus_tyontekija in taydennyskoulutus.taydennyskoulutukset_tyontekijat.all():
            if (existing_tyontekija := existing_tyontekija_qs
                    .filter(henkilo=taydennyskoulutus_tyontekija.tyontekija.henkilo).first()):
                # If new_vakajarjestaja already has Tyontekija referencing to the same Henkilo, add it to the
                # Taydennyskoulutus object and remove the old one
                TaydennyskoulutusTyontekija.objects.create(taydennyskoulutus=taydennyskoulutus,
                                                           tehtavanimike_koodi=taydennyskoulutus_tyontekija.tehtavanimike_koodi,
                                                           tyontekija=existing_tyontekija,
                                                           changed_by=taydennyskoulutus_tyontekija.changed_by)
                taydennyskoulutus_tyontekija.delete()

        # Assign permissions after changes have been made
        tyontekija_id_list, toimipaikka_oid_list_list = get_tyontekija_and_toimipaikka_lists_for_taydennyskoulutus(
            taydennyskoulutus.taydennyskoulutukset_tyontekijat.all()
        )
        # Combine toimipaikka_oids of old and existing tyontekija
        taydennyskoulutus_oid_set |= set(flatten_nested_list(toimipaikka_oid_list_list))
        for organisaatio_oid in taydennyskoulutus_oid_set:
            if organisaatio_oid:
                assign_object_permissions_to_taydennyskoulutus_groups(organisaatio_oid, Taydennyskoulutus,
                                                                      taydennyskoulutus)
        # Save Taydennyskoulutus without modifications so that new historical record is created
        taydennyskoulutus.save()


def _get_tyontekija_oid_set(new_vakajarjestaja, tyontekija):
    tyontekija_oid_set = set(tyontekija.palvelussuhteet
                             .values_list('tyoskentelypaikat__toimipaikka__organisaatio_oid', flat=True))
    tyontekija_oid_set.add(new_vakajarjestaja.organisaatio_oid)

    if existing_tyontekija := Tyontekija.objects.filter(henkilo=tyontekija.henkilo, vakajarjestaja=new_vakajarjestaja).first():
        # Add toimipaikka_oids of potentially existing tyontekija
        tyontekija_oid_set |= set(existing_tyontekija.palvelussuhteet
                                  .values_list('tyoskentelypaikat__toimipaikka__organisaatio_oid', flat=True))
    return tyontekija_oid_set


def _raise_error(msg):
    raise serializers.ValidationError({'errors': [msg]})
