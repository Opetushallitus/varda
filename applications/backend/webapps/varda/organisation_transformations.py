from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from rest_framework import serializers

from varda.models import (
    Toimipaikka,
    Lapsi,
    Maksutieto,
    Huoltajuussuhde,
    Tyontekija,
    Tutkinto,
    Taydennyskoulutus,
    TaydennyskoulutusTyontekija,
    VuokrattuHenkilosto,
    MaksutietoHuoltajuussuhde,
)
from varda.permission_groups import get_all_permission_groups_for_organization
from varda.permissions import (
    assign_taydennyskoulutus_permissions,
    assign_vuokrattu_henkilosto_permissions,
    assign_toimipaikka_permissions,
    delete_permissions_from_object_instance_by_oid,
    reassign_all_lapsi_permissions,
    reassign_all_tyontekija_permissions,
)


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
        _raise_error("new_vakajarjestaja and old_vakajarjestaja cannot be the same")

    # Check that transfer is kunta -> kunta or yksityinen -> yksityinen
    if new_vakajarjestaja.kunnallinen_kytkin != old_vakajarjestaja.kunnallinen_kytkin:
        _raise_error("only kunta -> kunta and yksityinen -> yksityinen transfers are supported")

    # Check that old_vakajarjestaja does not have PAOS Lapsi objects
    if Lapsi.objects.filter(paos_organisaatio=old_vakajarjestaja).exists():
        _raise_error("old_vakajarjestaja has PAOS Lapsi objects in its Toimipaikka objects")


def _transfer_toimipaikka_permissions_to_new_vakajarjestaja(new_vakajarjestaja, old_vakajarjestaja):
    toimipaikka_id_list = old_vakajarjestaja.toimipaikat.values_list("id", flat=True)
    toimipaikka_qs = Toimipaikka.objects.filter(id__in=toimipaikka_id_list)

    for toimipaikka in toimipaikka_qs:
        # Disassociate all users from Toimipaikka specific permission groups
        for group in get_all_permission_groups_for_organization(toimipaikka.organisaatio_oid):
            group.user_set.clear()

        # Change Organisaatio reference of Toimipaikka
        toimipaikka.vakajarjestaja = new_vakajarjestaja
        toimipaikka.save()

        # Reassign permissions
        assign_toimipaikka_permissions(toimipaikka, reassign=True)


def _get_vakajarjestaja_lapset_qs(vakajarjestaja):
    return Lapsi.objects.filter(
        Q(vakatoimija=vakajarjestaja)
        | (
            Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__vakajarjestaja=vakajarjestaja)
            & Q(paos_organisaatio=None)
        )
    ).distinct("id")


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
        toimipaikka_oid_set = set(
            lapsi.varhaiskasvatuspaatokset.values_list("varhaiskasvatussuhteet__toimipaikka__organisaatio_oid", flat=True)
        )

        # Check if new_vakajarjestaja already has same Lapsi object
        existing_lapsi = None
        if existing_lapsi_obj := existing_lapsi_qs.filter(henkilo=lapsi.henkilo).first():
            existing_lapsi = existing_lapsi_obj
            # Add toimipaikka_oids of existing Lapsi to the set
            toimipaikka_oid_set |= set(
                existing_lapsi.varhaiskasvatuspaatokset.values_list(
                    "varhaiskasvatussuhteet__toimipaikka__organisaatio_oid", flat=True
                )
            )

        if not existing_lapsi:
            # Change vakatoimija of Lapsi object
            lapsi.vakatoimija = new_vakajarjestaja
            lapsi.save()

            # Delete Henkilo permissions, only from old_vakajarjestaja, if old_vakajarjestaja does not have PAOS-lapsi
            # that remains
            if not Lapsi.objects.filter(oma_organisaatio=old_vakajarjestaja, henkilo=lapsi.henkilo).exists():
                delete_permissions_from_object_instance_by_oid(lapsi.henkilo, old_vakajarjestaja.organisaatio_oid)

        if existing_lapsi:
            transfer_vaka_data_to_different_lapsi(lapsi, existing_lapsi)
            # Lapsi related data was transferred to an existing Lapsi object, so delete the old one
            MaksutietoHuoltajuussuhde.objects.filter(huoltajuussuhde__lapsi=lapsi).delete()
            Huoltajuussuhde.objects.filter(lapsi=lapsi).delete()
            lapsi.delete()

        reassign_all_lapsi_permissions(existing_lapsi or lapsi)


def _transfer_vakapaatos_permissions_to_new_vakajarjestaja(lapsi, existing_lapsi):
    for vakapaatos in lapsi.varhaiskasvatuspaatokset.all():
        # Transfer vakapaatos to existing lapsi
        vakapaatos.lapsi = existing_lapsi
        vakapaatos.save()


def _transfer_maksutieto_permissions_to_new_vakajarjestaja(lapsi, existing_lapsi):
    for maksutieto in Maksutieto.objects.filter(huoltajuussuhteet__lapsi=lapsi).distinct():
        # Transfer Maksutieto object for existing Lapsi object
        for maksutieto_huoltajuussuhde in maksutieto.maksutiedot_huoltajuussuhteet.all():
            huoltajuussuhde = Huoltajuussuhde.objects.get(
                lapsi=existing_lapsi, huoltaja=maksutieto_huoltajuussuhde.huoltajuussuhde.huoltaja
            )
            MaksutietoHuoltajuussuhde.objects.create(huoltajuussuhde=huoltajuussuhde, maksutieto=maksutieto)
        # Save Maksutieto without modifications so that new historical record is created
        # and Maksutieto is reported as MODIFIED in e.g. Vipunen API requests
        maksutieto.save()


def _transfer_tyontekija_permissions_to_new_vakajarjestaja(new_vakajarjestaja, old_vakajarjestaja):
    """
    Parent method for transferring Tyontekija related permissions (Tyontekija, Tutkinto, Palvelussuhde,
    Tyoskentelypaikka, PidempiPoissaolo, Taydennyskoulutus) and VuokrattuHenkilosto to new Organisaatio
    :param new_vakajarjestaja: Organisaatio object which Tyontekija related data is transferred to
    :param old_vakajarjestaja: Organisaatio object which Tyontekija related data is transferred from
    """
    _transfer_vuokrattu_henkilosto_permissions_to_new_vakajarjestaja(new_vakajarjestaja, old_vakajarjestaja)
    taydennyskoulutus_list = _transfer_taydennyskoulutus_objects_to_new_vakajarjestaja(new_vakajarjestaja, old_vakajarjestaja)
    _transfer_tutkinto_permissions_to_new_vakajarjestaja(new_vakajarjestaja, old_vakajarjestaja)

    tyontekija_qs = Tyontekija.objects.filter(vakajarjestaja=old_vakajarjestaja)
    existing_tyontekija_qs = Tyontekija.objects.filter(vakajarjestaja=new_vakajarjestaja)
    for tyontekija in tyontekija_qs:
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

        if existing_tyontekija:
            _transfer_palvelussuhde_permissions_to_new_vakajarjestaja(tyontekija, existing_tyontekija)
            # Tyontekija related data was transferred to an existing Tyontekija object, so delete the old one
            tyontekija.delete()

        reassign_all_tyontekija_permissions(existing_tyontekija or tyontekija)

    # Reassign Taydennyskoulutus permissions now that Tyontekija changes have been made
    # (only one Organisaatio is related to each Taydennyskoulutus object)
    _transfer_taydennyskoulutus_permissions_to_new_vakajarjestaja(taydennyskoulutus_list)


def _transfer_vuokrattu_henkilosto_permissions_to_new_vakajarjestaja(new_vakajarjestaja, old_vakajarjestaja):
    for vuokrattu_henkilosto in VuokrattuHenkilosto.objects.filter(vakajarjestaja=old_vakajarjestaja):
        existing_vuokrattu_henkilosto = VuokrattuHenkilosto.objects.filter(
            vakajarjestaja=new_vakajarjestaja,
            kuukausi__month=vuokrattu_henkilosto.kuukausi.month,
            kuukausi__year=vuokrattu_henkilosto.kuukausi.year,
        ).first()
        if existing_vuokrattu_henkilosto:
            # new_vakajarjestaja already has VuokrattuHenkilosto object for this month
            existing_vuokrattu_henkilosto.tuntimaara += vuokrattu_henkilosto.tuntimaara
            existing_vuokrattu_henkilosto.tyontekijamaara += vuokrattu_henkilosto.tyontekijamaara
            existing_vuokrattu_henkilosto.save()
            # Delete old VuokrattuHenkilosto object
            vuokrattu_henkilosto.delete()
        else:
            # new_vakajarjestaja does not have VuokrattuHenkilosto object for this month so object can be
            # transferred
            vuokrattu_henkilosto.vakajarjestaja = new_vakajarjestaja
            vuokrattu_henkilosto.save()
            assign_vuokrattu_henkilosto_permissions(vuokrattu_henkilosto, reassign=True)


def _transfer_tutkinto_permissions_to_new_vakajarjestaja(new_vakajarjestaja, old_vakajarjestaja):
    for tutkinto in Tutkinto.objects.filter(vakajarjestaja=old_vakajarjestaja):
        if Tutkinto.objects.filter(
            vakajarjestaja=new_vakajarjestaja, henkilo=tutkinto.henkilo, tutkinto_koodi=tutkinto.tutkinto_koodi
        ).exists():
            # If new_vakajarjestaja already has duplicate Tutkinto object, delete the old one
            tutkinto.delete()
        else:
            # Update vakajarjestaja field
            tutkinto.vakajarjestaja = new_vakajarjestaja
            tutkinto.save()


def _transfer_palvelussuhde_permissions_to_new_vakajarjestaja(tyontekija, existing_tyontekija):
    for palvelussuhde in tyontekija.palvelussuhteet.all():
        # Transfer Palvelussuhde to existing Tyontekija
        palvelussuhde.tyontekija = existing_tyontekija
        palvelussuhde.save()


def _transfer_taydennyskoulutus_objects_to_new_vakajarjestaja(new_vakajarjestaja, old_vakajarjestaja):
    existing_tyontekija_qs = Tyontekija.objects.filter(vakajarjestaja=new_vakajarjestaja)

    taydennyskoulutus_list = []
    for taydennyskoulutus in Taydennyskoulutus.objects.filter(tyontekijat__vakajarjestaja=old_vakajarjestaja).distinct():
        for taydennyskoulutus_tyontekija in taydennyskoulutus.taydennyskoulutukset_tyontekijat.all():
            if existing_tyontekija := existing_tyontekija_qs.filter(
                henkilo=taydennyskoulutus_tyontekija.tyontekija.henkilo
            ).first():
                # If new_vakajarjestaja already has Tyontekija referencing to the same Henkilo, add it to the
                # Taydennyskoulutus object and remove the old one
                TaydennyskoulutusTyontekija.objects.create(
                    taydennyskoulutus=taydennyskoulutus,
                    tehtavanimike_koodi=taydennyskoulutus_tyontekija.tehtavanimike_koodi,
                    tyontekija=existing_tyontekija,
                )
                taydennyskoulutus_tyontekija.delete()
        # Save Taydennyskoulutus without modifications so that new historical record is created
        # and Taydennyskoulutus is reported as MODIFIED in e.g. Tilastokeskus API requests
        taydennyskoulutus.save()
        taydennyskoulutus_list.append(taydennyskoulutus)
    return taydennyskoulutus_list


def _transfer_taydennyskoulutus_permissions_to_new_vakajarjestaja(taydennyskoulutus_list):
    for taydennyskoulutus in taydennyskoulutus_list:
        assign_taydennyskoulutus_permissions(taydennyskoulutus, reassign=True)


def _raise_error(msg):
    raise serializers.ValidationError({"errors": [msg]})


def transfer_vaka_data_to_different_lapsi(old_lapsi, new_lapsi):
    _transfer_vakapaatos_permissions_to_new_vakajarjestaja(old_lapsi, new_lapsi)
    _transfer_maksutieto_permissions_to_new_vakajarjestaja(old_lapsi, new_lapsi)
