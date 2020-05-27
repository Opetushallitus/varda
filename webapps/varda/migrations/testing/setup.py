import datetime

from varda.migrations.production.setup import (get_vakajarjestaja_palvelukayttaja_permissions,
                                               get_vakajarjestaja_katselija_permissions,
                                               get_vakajarjestaja_paakayttaja_permissions,
                                               get_toimipaikka_tallentaja_permissions,
                                               get_huoltajatiedot_tallentaja_permissions,
                                               get_huoltajatiedot_katselija_permissions)


def add_groups_with_permissions():
    from django.contrib.auth.models import Group, Permission
    group_permission_array = [
        ('VARDA-KATSELIJA_1.2.246.562.10.9395737548811', get_vakajarjestaja_katselija_permissions()),
        ('VARDA-KATSELIJA_1.2.246.562.10.9395737548815', get_vakajarjestaja_katselija_permissions()),
        ('VARDA-KATSELIJA_1.2.246.562.10.93957375488', get_vakajarjestaja_katselija_permissions()),
        ('VARDA-KATSELIJA_1.2.246.562.10.34683023489', get_vakajarjestaja_katselija_permissions()),
        ('VARDA-KATSELIJA_1.2.246.562.10.93957375484', get_vakajarjestaja_katselija_permissions()),  # vakajarjestaja_4
        ('VARDA-KATSELIJA_1.2.246.562.10.9395737548810', get_vakajarjestaja_katselija_permissions()),  # toimipaikka_1
        ('VARDA-KATSELIJA_1.2.246.562.10.9395737548817', get_vakajarjestaja_katselija_permissions()),  # toimipaikka_5
        ('VARDA-PAAKAYTTAJA_1.2.246.562.10.93957375488', get_vakajarjestaja_paakayttaja_permissions()),
        ('VARDA-PAAKAYTTAJA_1.2.246.562.10.34683023489', get_vakajarjestaja_paakayttaja_permissions()),
        ('VARDA-PAAKAYTTAJA_1.2.246.562.10.93957375484', get_vakajarjestaja_paakayttaja_permissions()),  # vakajarjestaja_4
        ('VARDA-PALVELUKAYTTAJA_1.2.246.562.10.93957375484', get_vakajarjestaja_palvelukayttaja_permissions()),  # vakajarjestaja_4
        ('VARDA-TALLENTAJA_1.2.246.562.10.93957375488', get_vakajarjestaja_palvelukayttaja_permissions()),
        ('VARDA-PALVELUKAYTTAJA_1.2.246.562.10.93957375488', get_vakajarjestaja_palvelukayttaja_permissions()),
        ('VARDA-TALLENTAJA_1.2.246.562.10.9395737548810', get_toimipaikka_tallentaja_permissions()),
        ('VARDA-TALLENTAJA_1.2.246.562.10.34683023489', get_vakajarjestaja_palvelukayttaja_permissions()),
        ('VARDA-TALLENTAJA_1.2.246.562.10.9395737548815', get_toimipaikka_tallentaja_permissions()),  # toimipaikka_2
        ('VARDA-TALLENTAJA_1.2.246.562.10.9395737548817', get_toimipaikka_tallentaja_permissions()),  # toimipaikka_5
        ('VARDA-PALVELUKAYTTAJA_1.2.246.562.10.34683023489', get_vakajarjestaja_palvelukayttaja_permissions()),
        ('HUOLTAJATIETO_TALLENNUS_1.2.246.562.10.9395737548810', get_huoltajatiedot_tallentaja_permissions()),
        ('HUOLTAJATIETO_TALLENNUS_1.2.246.562.10.34683023489', get_huoltajatiedot_tallentaja_permissions()),
        ('HUOLTAJATIETO_TALLENNUS_1.2.246.562.10.93957375488', get_huoltajatiedot_tallentaja_permissions()),
        ('HUOLTAJATIETO_TALLENNUS_1.2.246.562.10.93957375484', get_huoltajatiedot_tallentaja_permissions()),  # vakajarjestaja_4
        ('HUOLTAJATIETO_TALLENNUS_1.2.246.562.10.9395737548817', get_huoltajatiedot_tallentaja_permissions()),  # toimipaikka_5
        ('HUOLTAJATIETO_KATSELU_1.2.246.562.10.9395737548810', get_huoltajatiedot_katselija_permissions()),
        ('HUOLTAJATIETO_KATSELU_1.2.246.562.10.93957375488', get_huoltajatiedot_katselija_permissions()),
        ('HUOLTAJATIETO_KATSELU_1.2.246.562.10.34683023489', get_huoltajatiedot_katselija_permissions()),
        ('HUOLTAJATIETO_KATSELU_1.2.246.562.10.93957375484', get_huoltajatiedot_katselija_permissions())  # vakajarjestaja_4
    ]

    for group_tuple in group_permission_array:
        group_obj = Group.objects.create(name=group_tuple[0])
        group_permissions = Permission.objects.filter(codename__in=group_tuple[1])
        group_obj.permissions.add(*group_permissions)


def add_test_users():
    from django.contrib.auth.models import Group, Permission, User
    from rest_framework.authtoken.models import Token
    group_palvelukayttaja = Group.objects.get(name='vakajarjestaja_palvelukayttaja')
    group_palvelukayttaja_vakajarjestaja_1 = Group.objects.get(name='VARDA-PALVELUKAYTTAJA_1.2.246.562.10.34683023489')
    group_palvelukayttaja_vakajarjestaja_2 = Group.objects.get(name='VARDA-PALVELUKAYTTAJA_1.2.246.562.10.93957375488')
    group_view_henkilo = Group.objects.get(name='vakajarjestaja_view_henkilo')
    group_tallentaja_vakajarjestaja_2 = Group.objects.get(name='VARDA-TALLENTAJA_1.2.246.562.10.93957375488')
    group_tallentaja_toimipaikka_1 = Group.objects.get(name='VARDA-TALLENTAJA_1.2.246.562.10.9395737548810')
    group_katselija_toimipaikka_4 = Group.objects.get(name='VARDA-KATSELIJA_1.2.246.562.10.9395737548811')
    group_tallentaja_vakajarjestaja_1 = Group.objects.get(name='VARDA-TALLENTAJA_1.2.246.562.10.34683023489')
    group_tallentaja_toimipaikka_5 = Group.objects.get(name='VARDA-TALLENTAJA_1.2.246.562.10.9395737548817')
    group_paakayttaja_vakajarjestaja_1 = Group.objects.get(name='VARDA-PAAKAYTTAJA_1.2.246.562.10.34683023489')
    group_paakayttaja_vakajarjestaja_2 = Group.objects.get(name='VARDA-PAAKAYTTAJA_1.2.246.562.10.93957375488')
    group_huoltajatiedot_tallentaja_toimipaikka_1 = Group.objects.get(name='HUOLTAJATIETO_TALLENNUS_1.2.246.562.10.9395737548810')
    group_huoltajatiedot_tallentaja_vakajarjestaja_1 = Group.objects.get(name='HUOLTAJATIETO_TALLENNUS_1.2.246.562.10.34683023489')
    group_huoltajatiedot_tallentaja_vakajarjestaja_2 = Group.objects.get(name='HUOLTAJATIETO_TALLENNUS_1.2.246.562.10.93957375488')
    group_huoltajatiedot_tallentaja_toimipaikka_5 = Group.objects.get(name='HUOLTAJATIETO_TALLENNUS_1.2.246.562.10.9395737548817')

    user_tester = User.objects.create(username='tester', password='pbkdf2_sha256$120000$4IdDHxUJJSE6$N18zHZK02yA3KxNeTcDS4t6Ytsn2ZOLO6QLDXNT/8Yo=')
    Token.objects.create(user=user_tester, key='916b7ca8f1687ec3462b4a35d0c5c6da0dbeedf3')
    user_tester.groups.add(group_view_henkilo)
    user_tester.groups.add(group_tallentaja_toimipaikka_1)
    user_tester.groups.add(group_katselija_toimipaikka_4)
    user_tester.groups.add(group_huoltajatiedot_tallentaja_toimipaikka_1)
    user_tester.groups.add(group_huoltajatiedot_tallentaja_vakajarjestaja_1)
    add_toimipaikka_permission = Permission.objects.get(codename='add_toimipaikka')
    user_tester.user_permissions.add(add_toimipaikka_permission)  # Needed for varda/examples/add_toimipaikka -test

    user_tester2 = User.objects.create(username='tester2', password='pbkdf2_sha256$120000$gNFFj5K8ZgTu$quUQQlMXZCs+1mG+nbBpTS/VXRZAy47XkR7EoioNLkQ=')
    user_tester2.groups.add(group_view_henkilo)
    user_tester2.groups.add(group_tallentaja_vakajarjestaja_1)
    user_tester2.groups.add(group_huoltajatiedot_tallentaja_vakajarjestaja_1)

    user_tester3 = User.objects.create(username='tester3', password='pbkdf2_sha256$150000$kfJSJbENiF5k$tZ3aa9ErAy1Ciszx40KdRMU787p7HnKHjVOQ+lzDF7U=')
    user_tester3.groups.add(group_view_henkilo)
    user_tester3.groups.add(group_paakayttaja_vakajarjestaja_2)

    user_tester4 = User.objects.create(username='tester4', password='pbkdf2_sha256$150000$LFrFAT6FakMM$VuLb0n11tVR0tlIBAmykLWP4an5zv4XWseGHJDlnsWk=')
    user_tester4.groups.add(group_view_henkilo)
    user_tester4.groups.add(group_paakayttaja_vakajarjestaja_1)

    user_tester5 = User.objects.create(username='tester5', password='pbkdf2_sha256$150000$ZX2pJZZ34sR6$XUs0RUe6IZYNdn7vYxIvm+05Ruw4brTbYG70Q3oH31s=')
    user_tester5.groups.add(group_tallentaja_vakajarjestaja_2)
    user_tester5.groups.add(group_view_henkilo)

    user_varda_testi = User.objects.create(username='varda-testi', password='pbkdf2_sha256$120000$0wwPCIArT7tR$OVGZGiJoJe7wqcP1CG4orfA31MUrMXlI5fHcnOUzcIw=')
    user_varda_testi.groups.add(group_palvelukayttaja)
    user_varda_testi.groups.add(group_view_henkilo)

    user_tester_e2e = User.objects.create(username='tester-e2e', password='pbkdf2_sha256$120000$6ihvwx47epob$a2xDB6OLThL4eeEuMVw8+3QB1QBxi5hU2gZxnMwA2nE=')
    user_tester_e2e.groups.add(group_palvelukayttaja)
    user_tester_e2e.groups.add(group_view_henkilo)

    user_palvelukayttaja_vakajarjestaja_1 = User.objects.create(username='pkvakajarjestaja1', password='pbkdf2_sha256$150000$rBZO8vnXaxun$MhKN0NOCnasVgrMsIkYfIBXaBDdRiRy8J7WQM62bARY=')
    user_palvelukayttaja_vakajarjestaja_1.groups.add(group_palvelukayttaja_vakajarjestaja_1)
    user_palvelukayttaja_vakajarjestaja_1.groups.add(group_view_henkilo)

    user_palvelukayttaja_vakajarjestaja_2 = User.objects.create(username='pkvakajarjestaja2', password='pbkdf2_sha256$150000$ptRhdza1ttgB$IJdKerCPdzhC/wDME/rUVzFTKflh2coUuaCGWomg+Lo=')
    user_palvelukayttaja_vakajarjestaja_2.groups.add(group_palvelukayttaja_vakajarjestaja_2)
    user_palvelukayttaja_vakajarjestaja_2.groups.add(group_view_henkilo)

    user_tester6 = User.objects.create(username='tester6', password='pbkdf2_sha256$150000$S3mQ66CWYdSO$o9T08pdVyIZFqbdC8pK5cMk2O64d3xfQdw2x2vzr4M8=')
    user_tester6.groups.add(group_huoltajatiedot_tallentaja_vakajarjestaja_1)
    user_tester6.groups.add(group_view_henkilo)

    user_tester7 = User.objects.create(username='tester7', password='pbkdf2_sha256$150000$9fuSiDHlpxu4$qpRt5+aPs8Fd9VsI0XPjOvMHCN7LF+VbSJLyIghrNks=')
    user_tester7.groups.add(group_huoltajatiedot_tallentaja_vakajarjestaja_2)
    user_tester7.groups.add(group_view_henkilo)

    user_tester8 = User.objects.create(username='tester8', password='pbkdf2_sha256$150000$e5HLX1BadPnp$4H0r3yNEbiaTZ2yJ07HFK+8GsUM5JwKGNa/O727IOtI=')
    user_tester8.groups.add(group_tallentaja_toimipaikka_5)
    user_tester8.groups.add(group_view_henkilo)

    user_tester9 = User.objects.create(username='tester9', password='pbkdf2_sha256$150000$ntAfCrXVuXnI$A63mBzAb7EzHDdR6jTSGZDmmYj0OtfbgetIFbtBZXBo=')
    user_tester9.groups.add(group_huoltajatiedot_tallentaja_toimipaikka_5)
    user_tester9.groups.add(group_view_henkilo)

    User.objects.create(username='tester-no-known-privileges', password='pbkdf2_sha256$120000$6ihvwx47epob$a2xDB6OLThL4eeEuMVw8+3QB1QBxi5hU2gZxnMwA2nE=')


def create_vakajarjestajat():
    from django.contrib.auth.models import User
    from varda.permission_groups import assign_permissions_to_vakajarjestaja_obj
    from varda.models import VakaJarjestaja

    tester_user = User.objects.get(username='tester')
    tester2_user = User.objects.get(username='tester2')
    varda_testi_user = User.objects.get(username='varda-testi')
    tester_e2e_user = User.objects.get(username='tester-e2e')

    VakaJarjestaja.objects.create(
        nimi='Tester2 organisaatio',
        y_tunnus='8500570-7',
        organisaatio_oid='1.2.246.562.10.34683023489',
        kunta_koodi='091',
        sahkopostiosoite='organization@domain.com',
        tilinumero='FI37 1590 3000 0007 76',
        kayntiosoite='Testerkatu 2',
        kayntiosoite_postinumero='00001',
        kayntiosoite_postitoimipaikka='Testilä',
        postiosoite='Testerkatu 2',
        postitoimipaikka='Testilä',
        postinumero='00001',
        puhelinnumero='+358101234567',
        yritysmuoto='KUNTA',
        alkamis_pvm='2017-02-03',
        paattymis_pvm=None,
        changed_by=tester2_user,
        integraatio_organisaatio=True
    )

    VakaJarjestaja.objects.create(
        nimi='Tester organisaatio',
        y_tunnus='1825748-8',
        organisaatio_oid='1.2.246.562.10.93957375488',
        kunta_koodi='049',
        sahkopostiosoite='organization@domain.com',
        tilinumero='FI92 2046 1800 0628 04',
        kayntiosoite='Testerkatu 1',
        kayntiosoite_postinumero='00001',
        kayntiosoite_postitoimipaikka='Testilä',
        postiosoite='Testerkatu 1',
        postitoimipaikka='Testilä',
        postinumero='00001',
        puhelinnumero='+358101234567',
        alkamis_pvm='2017-02-03',
        paattymis_pvm=None,
        ytjkieli='FI',
        yritysmuoto='OSAKEYHTIO',
        changed_by=tester_user
    )

    VakaJarjestaja.objects.create(
        nimi='varda-testi organisaatio',
        y_tunnus='2617455-1',
        organisaatio_oid='1.2.246.562.10.93957375486',
        kunta_koodi='',
        sahkopostiosoite='varda-testi@email.fi',
        tilinumero='FI92 2046 1800 0628 04',
        kayntiosoite='Testilä 3',
        kayntiosoite_postinumero='10001',
        kayntiosoite_postitoimipaikka='Testilä',
        postiosoite='Testilä3',
        postitoimipaikka='Testilä',
        postinumero='10001',
        puhelinnumero='+358451234567',
        alkamis_pvm='2018-09-13',
        paattymis_pvm=None,
        changed_by=varda_testi_user
    )

    VakaJarjestaja.objects.create(
        nimi='Frontti organisaatio',
        y_tunnus='2156233-6',
        organisaatio_oid='1.2.246.562.10.93957375484',
        kunta_koodi='230',
        sahkopostiosoite='frontti@end.com',
        tilinumero='FI92 2046 1800 0628 04',
        kayntiosoite='Fronttikuja 12',
        kayntiosoite_postinumero='54321',
        kayntiosoite_postitoimipaikka='Fronttila',
        postiosoite='Fronttikuja 12',
        postitoimipaikka='Fronttila',
        postinumero='54321',
        puhelinnumero='+358505432109',
        yritysmuoto='KUNTAYHTYMA',
        alkamis_pvm='2018-09-25',
        paattymis_pvm=None,
        changed_by=tester_e2e_user
    )

    assign_permissions_to_vakajarjestaja_obj('1.2.246.562.10.34683023489')
    assign_permissions_to_vakajarjestaja_obj('1.2.246.562.10.93957375488')
    assign_permissions_to_vakajarjestaja_obj('1.2.246.562.10.93957375486')
    assign_permissions_to_vakajarjestaja_obj('1.2.246.562.10.93957375484')


def create_toimipaikat_and_painotukset():
    from django.contrib.auth.models import Group, User
    from guardian.shortcuts import assign_perm
    from varda.permission_groups import assign_permissions_to_toimipaikka_obj, assign_object_level_permissions
    from varda.models import KieliPainotus, ToiminnallinenPainotus, Toimipaikka, VakaJarjestaja

    tester_user = User.objects.get(username='tester')
    tester2_user = User.objects.get(username='tester2')
    tester_e2e_user = User.objects.get(username='tester-e2e')

    vakajarjestaja_tester_obj = VakaJarjestaja.objects.filter(nimi='Tester organisaatio')[0]
    vakajarjestaja_tester2_obj = VakaJarjestaja.objects.filter(nimi='Tester2 organisaatio')[0]
    vakajarjestaja_4_obj = VakaJarjestaja.objects.get(id=4)

    toimipaikka_1 = Toimipaikka.objects.create(
        vakajarjestaja=vakajarjestaja_tester_obj,
        nimi='Espoo',
        nimi_sv='Esbo',
        organisaatio_oid='1.2.246.562.10.9395737548810',
        kayntiosoite='Keilaranta 14',
        kayntiosoite_postitoimipaikka='Espoo',
        kayntiosoite_postinumero='02100',
        postiosoite='Keilaranta 14',
        postitoimipaikka='Espoo',
        postinumero='02100',
        kunta_koodi='091',
        puhelinnumero='+35810123456',
        sahkopostiosoite='test1@espoo.fi',
        kasvatusopillinen_jarjestelma_koodi='kj02',
        toimintamuoto_koodi='tm01',
        asiointikieli_koodi=['FI', 'SV'],
        jarjestamismuoto_koodi=['jm01'],
        varhaiskasvatuspaikat=120,
        toiminnallinenpainotus_kytkin=True,
        kielipainotus_kytkin=True,
        alkamis_pvm='2017-02-03',
        paattymis_pvm=None,
        changed_by=tester_user,
        lahdejarjestelma='ORGANISAATIO'
    )

    Toimipaikka.objects.create(
        vakajarjestaja=vakajarjestaja_tester2_obj,
        nimi='Tester2 toimipaikka',
        nimi_sv='Tester2 toimipaikka sv',
        organisaatio_oid='1.2.246.562.10.9395737548815',
        kayntiosoite='Katukaksi',
        kayntiosoite_postitoimipaikka='Postitoimipaikkakolme',
        kayntiosoite_postinumero='00109',
        postiosoite='Katukaksi',
        postitoimipaikka='Postitoimipaikkakolme',
        postinumero='00109',
        kunta_koodi='091',
        puhelinnumero='+35810123456',
        sahkopostiosoite='test2@domain.com',
        kasvatusopillinen_jarjestelma_koodi='kj03',
        toimintamuoto_koodi='tm01',
        asiointikieli_koodi=['FI', 'SV'],
        jarjestamismuoto_koodi=['jm01'],
        varhaiskasvatuspaikat=200,
        toiminnallinenpainotus_kytkin=False,
        kielipainotus_kytkin=False,
        alkamis_pvm='2017-08-02',
        paattymis_pvm=None,
        changed_by=tester2_user
    )

    toimipaikka_3 = Toimipaikka.objects.create(
        vakajarjestaja=vakajarjestaja_tester2_obj,
        nimi='Paivakoti kukkanen',
        nimi_sv='Paivakoti kukkanen sv',
        organisaatio_oid='',
        kayntiosoite='Pasilankatu 123',
        kayntiosoite_postitoimipaikka='Helsinki',
        kayntiosoite_postinumero='00109',
        postiosoite='Pasilankatu 123',
        postitoimipaikka='Helsinki',
        postinumero='00109',
        kunta_koodi='091',
        puhelinnumero='+35810123456',
        sahkopostiosoite='test3@domain.com',
        kasvatusopillinen_jarjestelma_koodi='kj04',
        toimintamuoto_koodi='tm01',
        asiointikieli_koodi=['SV'],
        jarjestamismuoto_koodi=['jm01'],
        varhaiskasvatuspaikat=100,
        toiminnallinenpainotus_kytkin=True,
        kielipainotus_kytkin=False,
        alkamis_pvm='2015-08-22',
        paattymis_pvm=None,
        changed_by=tester2_user
    )

    toimipaikka_4 = Toimipaikka.objects.create(
        vakajarjestaja=vakajarjestaja_tester_obj,
        nimi='Espoo_2',
        nimi_sv='Esbo_2',
        organisaatio_oid='1.2.246.562.10.9395737548811',
        kayntiosoite='Keilaranta 41',
        kayntiosoite_postitoimipaikka='Espoo',
        kayntiosoite_postinumero='02100',
        postiosoite='Keilaranta 41',
        postitoimipaikka='Espoo',
        postinumero='02100',
        kunta_koodi='091',
        puhelinnumero='+35810654321',
        sahkopostiosoite='test2@espoo.fi',
        kasvatusopillinen_jarjestelma_koodi='kj04',
        toimintamuoto_koodi='tm03',
        asiointikieli_koodi=['FI'],
        jarjestamismuoto_koodi=['jm03'],
        varhaiskasvatuspaikat=150,
        toiminnallinenpainotus_kytkin=True,
        kielipainotus_kytkin=True,
        alkamis_pvm='2017-01-03',
        paattymis_pvm=None,
        changed_by=tester_user
    )

    Toimipaikka.objects.create(
        vakajarjestaja=vakajarjestaja_tester_obj,
        nimi='Espoo_3',
        nimi_sv='Esbo_3',
        organisaatio_oid='1.2.246.562.10.9395737548817',
        kayntiosoite='Espoonkeskus 5',
        kayntiosoite_postitoimipaikka='Espoo',
        kayntiosoite_postinumero='02100',
        postiosoite='Espoonkeskus 5',
        postitoimipaikka='Espoo',
        postinumero='02100',
        kunta_koodi='091',
        puhelinnumero='+35810654321',
        sahkopostiosoite='test2@espoo.fi',
        kasvatusopillinen_jarjestelma_koodi='kj04',
        toimintamuoto_koodi='tm03',
        asiointikieli_koodi=['FI'],
        jarjestamismuoto_koodi=['jm03'],
        varhaiskasvatuspaikat=150,
        toiminnallinenpainotus_kytkin=True,
        kielipainotus_kytkin=True,
        alkamis_pvm='2017-01-03',
        paattymis_pvm=None,
        changed_by=tester_user
    )

    Toimipaikka.objects.create(
        vakajarjestaja=vakajarjestaja_4_obj,
        nimi='Espoo_3',
        nimi_sv='Esbo_3',
        organisaatio_oid='1.2.246.562.10.9395737548812',
        kayntiosoite='Espoonkeskus 5',
        kayntiosoite_postitoimipaikka='Espoo',
        kayntiosoite_postinumero='02100',
        postiosoite='Espoonkeskus 5',
        postitoimipaikka='Espoo',
        postinumero='02100',
        kunta_koodi='091',
        puhelinnumero='+35810654321',
        sahkopostiosoite='test3@espoo.fi',
        kasvatusopillinen_jarjestelma_koodi='kj04',
        toimintamuoto_koodi='tm03',
        asiointikieli_koodi=['FI'],
        jarjestamismuoto_koodi=['jm03'],
        varhaiskasvatuspaikat=150,
        toiminnallinenpainotus_kytkin=True,
        kielipainotus_kytkin=True,
        alkamis_pvm='2017-01-03',
        paattymis_pvm=None,
        changed_by=tester_e2e_user
    )

    assign_permissions_to_toimipaikka_obj('1.2.246.562.10.9395737548810', '1.2.246.562.10.93957375488')
    assign_permissions_to_toimipaikka_obj('1.2.246.562.10.9395737548815', '1.2.246.562.10.34683023489')
    assign_permissions_to_toimipaikka_obj('1.2.246.562.10.9395737548811', '1.2.246.562.10.93957375488')
    assign_permissions_to_toimipaikka_obj('1.2.246.562.10.9395737548817', '1.2.246.562.10.93957375488')
    assign_permissions_to_toimipaikka_obj('1.2.246.562.10.9395737548812', '1.2.246.562.10.93957375484')

    group_tallentaja_tester2_vakajarjestaja = Group.objects.get(name='VARDA-TALLENTAJA_1.2.246.562.10.34683023489')
    assign_perm('view_toimipaikka', group_tallentaja_tester2_vakajarjestaja, toimipaikka_3)
    assign_perm('change_toimipaikka', group_tallentaja_tester2_vakajarjestaja, toimipaikka_3)

    toiminnallinenpainotus_1 = ToiminnallinenPainotus.objects.create(
        toimipaikka=toimipaikka_1,
        toimintapainotus_koodi='tp01',
        alkamis_pvm='2017-02-10',
        paattymis_pvm=None,
        changed_by=tester_user
    )

    toiminnallinenpainotus_2 = ToiminnallinenPainotus.objects.create(
        toimipaikka=toimipaikka_4,
        toimintapainotus_koodi='tp03',
        alkamis_pvm='2017-12-29',
        paattymis_pvm=None,
        changed_by=tester_user
    )

    kielipainotus_1 = KieliPainotus.objects.create(
        toimipaikka=toimipaikka_1,
        kielipainotus_koodi='FI',
        alkamis_pvm='2017-02-10',
        paattymis_pvm=None,
        changed_by=tester_user
    )

    kielipainotus_2 = KieliPainotus.objects.create(
        toimipaikka=toimipaikka_4,
        kielipainotus_koodi='EN',
        alkamis_pvm='2017-12-30',
        paattymis_pvm=None,
        changed_by=tester_user
    )

    assign_object_level_permissions('1.2.246.562.10.9395737548810', ToiminnallinenPainotus, toiminnallinenpainotus_1)
    assign_object_level_permissions('1.2.246.562.10.9395737548811', ToiminnallinenPainotus, toiminnallinenpainotus_2)
    assign_object_level_permissions('1.2.246.562.10.9395737548810', KieliPainotus, kielipainotus_1)
    assign_object_level_permissions('1.2.246.562.10.9395737548811', KieliPainotus, kielipainotus_2)


def create_henkilot():
    from django.contrib.auth.models import Group, User
    from guardian.shortcuts import assign_perm
    from varda.models import Henkilo

    tester_user = User.objects.get(username='tester')
    tester2_user = User.objects.get(username='tester2')
    vakajarjestaja_view_henkilo_group = Group.objects.get(name='vakajarjestaja_view_henkilo')

    henkilo_1 = Henkilo.objects.create(
        henkilotunnus='gAAAAABbo6PKTYHJdBqTmqyMAOuRy1coM2sTowZQjpt9xXfcJD8A-d68wCsKUpBKRvBO1TbP52cwIwd4OLUqNGtPSgVv_rC4Xg==',
        henkilotunnus_unique_hash='c0fb153e45c67559455852a690ab27cb39dff5d9703963b115230c44ea7444fb',
        syntyma_pvm='1956-04-12',
        henkilo_oid='',
        etunimet='Matti',
        kutsumanimi='Matti',
        sukunimi='Meikäläinen',
        aidinkieli_koodi='FI',
        kotikunta_koodi='091',
        turvakielto=False,
        sukupuoli_koodi=1,
        katuosoite='Keilaranta 14',
        postinumero='02101',
        postitoimipaikka='Espoo',
        changed_by=tester_user
    )

    henkilo_2 = Henkilo.objects.create(
        henkilotunnus='gAAAAABbo6TgMvkrjjiNaT1xGPvUk1rqbhfjqdI0y5P3nU2Xdp9b-2PYYY4nLezsmbYnEOk6knStVmKySdaZZ_1C9z9yr3b-zg==',
        henkilotunnus_unique_hash='4f69af70513bb6d4bc581137ecfb8582e079217b514ac0f3e7113f8a1367ff9f',
        syntyma_pvm='2014-01-01',
        henkilo_oid='1.2.246.562.24.47279942650',
        etunimet='Pekka',
        kutsumanimi='Pekka',
        sukunimi='Virtanen',
        aidinkieli_koodi='FI',
        kotikunta_koodi='049',
        turvakielto=False,
        sukupuoli_koodi=1,
        katuosoite='Torikatu 11 as 1',
        postinumero='53100',
        postitoimipaikka='Lappeenranta',
        changed_by=tester_user
    )

    henkilo_3 = Henkilo.objects.create(
        henkilotunnus='gAAAAABbo6UfCt9BdvOHbmIJy8PP6PkX1AjRiqF1gIRyqJtOO2LXKvPln7ZKKm1VQ5wiavuQtTh0ZGOj2qnGIIwtHVLIyNF57w==',
        henkilotunnus_unique_hash='2a84ca78ca692571d8db910a39d2734c49fa6149afc36bf5d02162061c6b5343',
        syntyma_pvm='2016-05-12',
        henkilo_oid='1.2.246.562.24.58672764848',
        etunimet='Susanna',
        kutsumanimi='Susanna',
        sukunimi='Virtanen',
        aidinkieli_koodi='FI',
        kotikunta_koodi='091',
        turvakielto=False,
        sukupuoli_koodi=2,
        katuosoite='Helsinkitie 1',
        postinumero='00109',
        postitoimipaikka='Helsinki',
        changed_by=tester_user
    )

    # 020476-321F
    henkilo_4 = Henkilo.objects.create(
        henkilotunnus='gAAAAABbo6VJ1ljhlAW352ePbRt2_xz926jBsXlyFpzy2tkX8iqHhz7QVOeHHboUQZ-aZfqtXt8R0DLQSOXFF6D7DoBbYNXnAQ==',
        henkilotunnus_unique_hash='520313b75faa8b56589e39c32b550f9ccb96c5cdff4fc137d118d04446773fc2',
        syntyma_pvm='1976-04-02',
        henkilo_oid='1.2.987654321',
        etunimet='Pauliina',
        kutsumanimi='Pauliina',
        sukunimi='Virtanen',
        aidinkieli_koodi='FI',
        kotikunta_koodi='049',
        turvakielto=False,
        sukupuoli_koodi=2,
        katuosoite='Torikatu 11 as 1',
        postinumero='53100',
        postitoimipaikka='Lappeenranta',
        changed_by=tester_user
    )

    henkilo_5 = Henkilo.objects.create(
        henkilotunnus='gAAAAABbo6WBxWFYoGcrNFHRrASpVO5w8srRrqkj34EaAwXz1rJm2kApH8aYc4E0o7SswHsMLtGeWrSgpHI0av3q7tKErR2d_Q==',
        henkilotunnus_unique_hash='c4ca5208ff889171f704c288586833d902fb1286e638330975a66095dad6e9df',
        syntyma_pvm='1986-03-12',
        henkilo_oid='',
        etunimet='Pertti',
        kutsumanimi='Pertti',
        sukunimi='Virtanen',
        aidinkieli_koodi='FI',
        kotikunta_koodi='049',
        turvakielto=False,
        sukupuoli_koodi=1,
        katuosoite='Torikatu 11 as 1',
        postinumero='53100',
        postitoimipaikka='Lappeenranta',
        changed_by=tester_user
    )

    henkilo_6 = Henkilo.objects.create(
        henkilotunnus='gAAAAABbo6WgYC0e12aJEf84P68IweQwa7wpnyoByGQsrtwM-McKU6SEXPB85_LObZa-DYWN4GQ7DOT2iqvsnkzgpW5BAHK5zA==',
        henkilotunnus_unique_hash='fda31b3595f9a7734f098bee191467825aeba25e2ee1811270801b9d015d7b62',
        syntyma_pvm='1966-02-13',
        henkilo_oid='',
        etunimet='Lasse',
        kutsumanimi='Lasse',
        sukunimi='Manner',
        aidinkieli_koodi='FI',
        kotikunta_koodi='091',
        turvakielto=False,
        sukupuoli_koodi=1,
        katuosoite='Mannertie 5',
        postinumero='02100',
        postitoimipaikka='Espoo',
        changed_by=tester_user
    )

    henkilo_7 = Henkilo.objects.create(
        henkilotunnus='gAAAAABbo6XWDtGt7DtER5vt3boz4t7zxK5F4LRnDplK8-DQ-pGVPBWLsATHP3CFGZrL1OIixjfI3dwCo1GW-9BfDj7AT5FZSw==',
        henkilotunnus_unique_hash='b91f70282091d40bc3e49a9dbe85c6a785d661690c4b9a95435356c4cc414417',
        syntyma_pvm='1934-03-17',
        henkilo_oid='1.2.246.562.24.49084901392',
        etunimet='Tuula-Testi',
        kutsumanimi='Tuula',
        sukunimi='Vanhanen',
        aidinkieli_koodi='FI',
        kotikunta_koodi='091',
        turvakielto=False,
        sukupuoli_koodi=2,
        katuosoite='Keilaranta 14',
        postinumero='02101',
        postitoimipaikka='Espoo',
        changed_by=tester2_user
    )

    henkilo_8 = Henkilo.objects.create(
        henkilotunnus='gAAAAABbo6X6VW8yiNVQqpFKGl_4JS-VEA12mMn-ajatHro5RR1_fYyocLrV1197TvFU5J0Yz51LZ6_1TyU7Erb3UasXVtUR6Q==',
        henkilotunnus_unique_hash='cb31a7a3d13fbb0e1419e5c4cdf8e93d6c67a2274659266a8d51c44896ddd292',
        syntyma_pvm='1948-05-11',
        henkilo_oid='',
        etunimet='Huoltaja',
        kutsumanimi='Huoltaja',
        sukunimi='Vanhanen',
        aidinkieli_koodi='FI',
        kotikunta_koodi='091',
        turvakielto=True,
        sukupuoli_koodi=1,
        katuosoite='Keilaranta 14',
        postinumero='02101',
        postitoimipaikka='Espoo',
        changed_by=tester2_user
    )

    # 120699-985W
    henkilo_9 = Henkilo.objects.create(
        henkilotunnus='gAAAAABdAQLPSh7CX77-E6zYwR7A8XmG-DuuIft_X-4ImEdKeMDEDnizZCAzOeUjVYl_uj3ihLh-fZBA7oRyBfFjLlMUiyFV6g==',
        henkilotunnus_unique_hash='6a9769730421705f70bac9a06ed68e70d1344c28a22878037b16a6099fb0f1a6',
        syntyma_pvm='1948-05-11',
        henkilo_oid='1.2.246.562.24.6815981182311',
        etunimet='Arpa Noppa',
        kutsumanimi='Arpa',
        sukunimi='Kuutio',
        aidinkieli_koodi='FI',
        kotikunta_koodi='091',
        turvakielto=False,
        sukupuoli_koodi=1,
        katuosoite='Keilaranta 14',
        postinumero='02101',
        postitoimipaikka='Espoo',
        changed_by=tester2_user
    )

    henkilo_10 = Henkilo.objects.create(
        henkilotunnus='',
        henkilotunnus_unique_hash='',
        syntyma_pvm='1948-05-11',
        henkilo_oid='1.2.246.562.24.6815481182312',
        etunimet='Hetuton',
        kutsumanimi='Hetuton',
        sukunimi='Testi',
        aidinkieli_koodi='FI',
        kotikunta_koodi='091',
        turvakielto=False,
        sukupuoli_koodi=1,
        katuosoite='Keilaranta 14',
        postinumero='02101',
        postitoimipaikka='Espoo',
        changed_by=tester2_user
    )

    # 220616A322J
    henkilo_11 = Henkilo.objects.create(
        henkilotunnus='gAAAAABenZxubIsJZrpDfyDegO9lStbOzddn4FYEbg3v-TS1xM0bMWXQ7m0LtMGL2pyQZPVpje6y2jDXxvpteLy1EoJOANG0Qw==',
        henkilotunnus_unique_hash='3b9ae94f89f3f56270b200485f3ecc47e966e542665402ebc30c1b77cebc2784',
        syntyma_pvm='2016-06-22',
        henkilo_oid='1.2.246.562.24.7777777777777',
        etunimet='Mira',
        kutsumanimi='Mira',
        sukunimi='Mairinen',
        aidinkieli_koodi='EN',
        kotikunta_koodi='049',
        turvakielto=False,
        sukupuoli_koodi=2,
        katuosoite='Koivukuja 14',
        postinumero='02101',
        postitoimipaikka='Espoo',
        changed_by=tester2_user
    )

    # 291090-398U
    henkilo_12 = Henkilo.objects.create(
        henkilotunnus='gAAAAABenaWG3mvY4m1yDf9vOD5kmM6zPAj0Lm9evTQrkRU4AuTEt0PPTmyxBaN7RAvo7HIycpmQzUKsFw-rrSpqwB9z8izObw==',
        henkilotunnus_unique_hash='71759fee33ea6ef42c7c0a064a9369370411d7d9a989fb58148379ee69634862',
        syntyma_pvm='1990-10-29',
        henkilo_oid='1.2.246.562.24.7777777777788',
        etunimet='Mari',
        kutsumanimi='Mari',
        sukunimi='Mairinen',
        aidinkieli_koodi='JP',
        kotikunta_koodi='049',
        turvakielto=False,
        sukupuoli_koodi=2,
        katuosoite='Koivukuja 14',
        postinumero='02101',
        postitoimipaikka='Espoo',
        changed_by=tester2_user
    )

    # 071119A884T
    henkilo_13 = Henkilo.objects.create(
        henkilotunnus='gAAAAABeqDLLKoxnhplzrNEgkPbv0TUQvS2dx_ft0lsIBrhlMJX7VLkUhhnCEtERjW_bZZAbgjavc9GGvFIk-6_bzGQv9qIqCQ==',
        henkilotunnus_unique_hash='c0a057089d3f1c7b5b6e03c07b8f9e3caea4a566aae3ba76b42509d47adcd55f',
        syntyma_pvm='1990-10-29',
        henkilo_oid='1.2.246.562.24.7777777777766',
        etunimet='Minna Maija',
        kutsumanimi='Maija',
        sukunimi='Suroinen',
        aidinkieli_koodi='FI',
        kotikunta_koodi='049',
        turvakielto=False,
        sukupuoli_koodi=2,
        katuosoite='Kannistokatu 14',
        postinumero='02101',
        postitoimipaikka='Espoo',
        changed_by=tester2_user
    )

    # 291180-7071
    henkilo_14 = Henkilo.objects.create(
        henkilotunnus='gAAAAABeqDPZvYP3UiGMdjk3DUieipMnFY8yOQ0HgxkukZh9kTYvDmWjzvjZ2BcSQS9mMYWh2YAIQf8NQPkNCNmzmpir_ytkPA==',
        henkilotunnus_unique_hash='da3d4187e11092380164be1feb310544671c1f36d9164db7202340195a91f0c3',
        syntyma_pvm='1990-10-29',
        henkilo_oid='1.2.246.562.24.7777777777755',
        etunimet='Jouni Janne',
        kutsumanimi='Jouni',
        sukunimi='Suroinen',
        aidinkieli_koodi='JP',
        kotikunta_koodi='049',
        turvakielto=False,
        sukupuoli_koodi=2,
        katuosoite='Kannistokatu 14',
        postinumero='02101',
        postitoimipaikka='Espoo',
        changed_by=tester2_user
    )

    # 010280-952L Huoltaja jolla lapsi 010215A951T
    henkilo_15 = Henkilo.objects.create(
        henkilotunnus='gAAAAABdiMQHWzMtv1WMLLnWDaiTONIkyMsK5ugZUJm3Ke4d4PR8wLLUs27QVA-iK1t9Lev3zEwCwSbYiSp0Pw_tNix1Hx05mA==',
        henkilotunnus_unique_hash="94d31d49afa408f076996b5ba0317671f185f71b39ac0d1980f341b5b04fb07d",
        syntyma_pvm="1980-03-11",
        henkilo_oid="1.2.246.562.24.99924839517",
        etunimet="Tessa",
        kutsumanimi="Tessa",
        sukunimi="Testilä",
        aidinkieli_koodi="FI",
        kotikunta_koodi="915",
        turvakielto=False,
        sukupuoli_koodi=1,
        katuosoite="Koivukuja 4",
        postinumero="01230",
        postitoimipaikka="Vantaa",
        changed_by=tester_user
    )

    # huoltajan lapsi 010215A951T
    henkilo_16 = Henkilo.objects.create(
        henkilotunnus='gAAAAABdiMQH-7x0FQ8sN7JIIP1bFUgEBpWlqb7-fdHXWXVdpAU6iKR37gQYe48qLrKs-JRNm20gJQMkKNK3tY5nvYSN5y73rw==',
        henkilotunnus_unique_hash="eca80ee4b264ceb572db5a6244bae9c5141400921ec5b80a7d9a2262de495b11",
        syntyma_pvm="2018-03-11",
        henkilo_oid="1.2.246.562.24.86012997950",
        etunimet="Teila Aamu Runelma",
        kutsumanimi="Teila",
        sukunimi="Testilä",
        aidinkieli_koodi="FI",
        kotikunta_koodi="915",
        turvakielto=False,
        sukupuoli_koodi=1,
        katuosoite="Koivukuja 4",
        postinumero="01230",
        postitoimipaikka="Vantaa",
        changed_by=tester_user
    )

    assign_perm('view_henkilo', vakajarjestaja_view_henkilo_group, henkilo_1)
    assign_perm('view_henkilo', vakajarjestaja_view_henkilo_group, henkilo_2)
    assign_perm('view_henkilo', vakajarjestaja_view_henkilo_group, henkilo_3)
    assign_perm('view_henkilo', vakajarjestaja_view_henkilo_group, henkilo_4)
    assign_perm('view_henkilo', vakajarjestaja_view_henkilo_group, henkilo_5)
    assign_perm('view_henkilo', vakajarjestaja_view_henkilo_group, henkilo_6)
    assign_perm('view_henkilo', vakajarjestaja_view_henkilo_group, henkilo_7)
    assign_perm('view_henkilo', vakajarjestaja_view_henkilo_group, henkilo_8)
    assign_perm('view_henkilo', vakajarjestaja_view_henkilo_group, henkilo_9)
    assign_perm('view_henkilo', vakajarjestaja_view_henkilo_group, henkilo_10)
    assign_perm('view_henkilo', vakajarjestaja_view_henkilo_group, henkilo_11)
    assign_perm('view_henkilo', vakajarjestaja_view_henkilo_group, henkilo_12)
    assign_perm('view_henkilo', vakajarjestaja_view_henkilo_group, henkilo_13)
    assign_perm('view_henkilo', vakajarjestaja_view_henkilo_group, henkilo_14)
    assign_perm('view_henkilo', vakajarjestaja_view_henkilo_group, henkilo_15)
    assign_perm('view_henkilo', vakajarjestaja_view_henkilo_group, henkilo_16)


def create_lapset():
    from django.contrib.auth.models import User
    from varda.misc import hash_string
    from varda.models import Henkilo, Lapsi, Toimipaikka, Varhaiskasvatuspaatos, Varhaiskasvatussuhde, VakaJarjestaja
    from varda.permission_groups import (assign_object_level_permissions, assign_toimipaikka_vakatiedot_paos_permissions,
                                         assign_vakajarjestaja_lapsi_paos_permissions, assign_vakajarjestaja_vakatiedot_paos_permissions,
                                         assign_toimipaikka_lapsi_paos_permissions)

    tester_user = User.objects.get(username='tester')
    tester2_user = User.objects.get(username='tester2')
    tester4_user = User.objects.get(username='tester4')

    vakajarjestaja_1_organisaatio_oid = '1.2.246.562.10.34683023489'
    vakajarjestaja_2_organisaatio_oid = '1.2.246.562.10.93957375488'
    vakajarjestaja_4_organisaatio_oid = '1.2.246.562.10.93957375484'

    vakajarjestaja_1 = VakaJarjestaja.objects.filter(organisaatio_oid=vakajarjestaja_1_organisaatio_oid)[0]
    vakajarjestaja_2 = VakaJarjestaja.objects.filter(organisaatio_oid=vakajarjestaja_2_organisaatio_oid)[0]
    vakajarjestaja_4 = VakaJarjestaja.objects.filter(organisaatio_oid=vakajarjestaja_4_organisaatio_oid)[0]

    toimipaikka_1_organisaatio_oid = '1.2.246.562.10.9395737548810'
    toimipaikka_2_organisaatio_oid = '1.2.246.562.10.9395737548815'
    toimipaikka_4_organisaatio_oid = '1.2.246.562.10.9395737548811'
    toimipaikka_5_organisaatio_oid = '1.2.246.562.10.9395737548817'

    toimipaikka_1 = Toimipaikka.objects.filter(organisaatio_oid=toimipaikka_1_organisaatio_oid)[0]
    toimipaikka_2 = Toimipaikka.objects.filter(organisaatio_oid=toimipaikka_2_organisaatio_oid)[0]
    toimipaikka_4 = Toimipaikka.objects.filter(organisaatio_oid=toimipaikka_4_organisaatio_oid)[0]
    toimipaikka_5 = Toimipaikka.objects.filter(organisaatio_oid=toimipaikka_5_organisaatio_oid)[0]

    henkilo_2 = Henkilo.objects.get(henkilotunnus_unique_hash=hash_string('010114A0013'))
    lapsi_1 = Lapsi.objects.create(
        henkilo=henkilo_2,
        changed_by=tester_user
    )

    henkilo_3 = Henkilo.objects.get(henkilotunnus_unique_hash=hash_string('120516A123V'))
    lapsi_2 = Lapsi.objects.create(
        henkilo=henkilo_3,
        changed_by=tester_user
    )

    henkilo_7 = Henkilo.objects.get(henkilotunnus_unique_hash=hash_string('170334-130B'))
    lapsi_3 = Lapsi.objects.create(
        henkilo=henkilo_7,
        changed_by=tester2_user
    )

    henkilo_9 = Henkilo.objects.get(henkilotunnus_unique_hash=hash_string('120699-985W'))
    lapsi_4 = Lapsi.objects.create(
        henkilo=henkilo_9,
        oma_organisaatio=vakajarjestaja_1,
        paos_organisaatio=vakajarjestaja_2,
        changed_by=tester2_user
    )

    henkilo_11 = Henkilo.objects.get(henkilotunnus_unique_hash=hash_string('220616A322J'))
    lapsi_5 = Lapsi.objects.create(
        henkilo=henkilo_11,
        oma_organisaatio=vakajarjestaja_4,
        paos_organisaatio=vakajarjestaja_2,
        changed_by=tester4_user
    )

    henkilo_16 = Henkilo.objects.get(henkilotunnus_unique_hash=hash_string('010215A951T'))
    lapsi_6 = Lapsi.objects.create(
        henkilo=henkilo_16,
        vakatoimija=vakajarjestaja_1,
        changed_by=tester_user
    )

    lapsi_7 = Lapsi.objects.create(
        henkilo=henkilo_16,
        vakatoimija=vakajarjestaja_2,
        changed_by=tester2_user
    )

    lapsi_8 = Lapsi.objects.create(
        henkilo=henkilo_16,
        oma_organisaatio=vakajarjestaja_1,
        paos_organisaatio=vakajarjestaja_2,
        changed_by=tester2_user
    )

    vakapaatos_1 = Varhaiskasvatuspaatos.objects.create(
        lapsi=lapsi_1,
        vuorohoito_kytkin=False,
        pikakasittely_kytkin=False,
        tuntimaara_viikossa=37.5,
        paivittainen_vaka_kytkin=False,
        kokopaivainen_vaka_kytkin=False,
        jarjestamismuoto_koodi='jm02',
        hakemus_pvm='2017-01-12',
        alkamis_pvm='2017-02-11',
        paattymis_pvm='2018-02-24',
        changed_by=tester_user
    )

    vakapaatos_2 = Varhaiskasvatuspaatos.objects.create(
        lapsi=lapsi_2,
        vuorohoito_kytkin=False,
        pikakasittely_kytkin=False,
        tuntimaara_viikossa=40.0,
        paivittainen_vaka_kytkin=True,
        kokopaivainen_vaka_kytkin=True,
        jarjestamismuoto_koodi='jm02',
        hakemus_pvm='2018-09-05',
        alkamis_pvm='2018-09-05',
        paattymis_pvm=None,
        changed_by=tester_user
    )

    vakapaatos_3 = Varhaiskasvatuspaatos.objects.create(
        lapsi=lapsi_3,
        vuorohoito_kytkin=False,
        pikakasittely_kytkin=False,
        tuntimaara_viikossa=39.0,
        paivittainen_vaka_kytkin=True,
        kokopaivainen_vaka_kytkin=True,
        jarjestamismuoto_koodi='jm01',
        hakemus_pvm='2018-09-05',
        alkamis_pvm='2018-09-05',
        paattymis_pvm=None,
        changed_by=tester2_user
    )

    vakapaatos_4 = Varhaiskasvatuspaatos.objects.create(
        lapsi=lapsi_4,
        vuorohoito_kytkin=False,
        pikakasittely_kytkin=False,
        tuntimaara_viikossa=39.0,
        paivittainen_vaka_kytkin=True,
        kokopaivainen_vaka_kytkin=True,
        jarjestamismuoto_koodi='jm03',
        hakemus_pvm='2018-09-05',
        alkamis_pvm='2018-09-05',
        paattymis_pvm=None,
        changed_by=tester2_user
    )

    vakapaatos_5 = Varhaiskasvatuspaatos.objects.create(
        lapsi=lapsi_5,
        vuorohoito_kytkin=False,
        pikakasittely_kytkin=False,
        tuntimaara_viikossa=39.0,
        paivittainen_vaka_kytkin=True,
        kokopaivainen_vaka_kytkin=True,
        jarjestamismuoto_koodi='jm03',
        hakemus_pvm='2018-10-05',
        alkamis_pvm='2018-10-05',
        paattymis_pvm=None,
        changed_by=tester4_user
    )

    vakapaatos_6 = Varhaiskasvatuspaatos.objects.create(
        lapsi=lapsi_6,
        vuorohoito_kytkin=True,
        pikakasittely_kytkin=True,
        tuntimaara_viikossa=37.5,
        paivittainen_vaka_kytkin=None,
        kokopaivainen_vaka_kytkin=None,
        jarjestamismuoto_koodi="jm03",
        hakemus_pvm="2019-01-01",
        alkamis_pvm="2019-02-11",
        paattymis_pvm="2019-10-24",
        changed_by=tester2_user
    )

    vakapaatos_7 = Varhaiskasvatuspaatos.objects.create(
        lapsi=lapsi_6,
        vuorohoito_kytkin=False,
        pikakasittely_kytkin=True,
        tuntimaara_viikossa=30.5,
        paivittainen_vaka_kytkin=True,
        kokopaivainen_vaka_kytkin=False,
        jarjestamismuoto_koodi="jm03",
        hakemus_pvm="2019-11-01",
        alkamis_pvm="2019-11-11",
        paattymis_pvm="2019-12-22",
        changed_by=tester2_user
    )

    # no vakasuhde to test huoltajanlapsi error situations
    vakapaatos_8 = Varhaiskasvatuspaatos.objects.create(
        lapsi=lapsi_7,
        vuorohoito_kytkin=False,
        pikakasittely_kytkin=True,
        tuntimaara_viikossa=30.5,
        paivittainen_vaka_kytkin=True,
        kokopaivainen_vaka_kytkin=False,
        jarjestamismuoto_koodi="jm04",
        hakemus_pvm="2019-01-01",
        alkamis_pvm="2019-11-11",
        paattymis_pvm="2019-12-22",
        changed_by=tester2_user
    )

    vakapaatos_9 = Varhaiskasvatuspaatos.objects.create(
        lapsi=lapsi_8,
        vuorohoito_kytkin=False,
        pikakasittely_kytkin=False,
        tuntimaara_viikossa=39.0,
        paivittainen_vaka_kytkin=True,
        kokopaivainen_vaka_kytkin=True,
        jarjestamismuoto_koodi='jm03',
        hakemus_pvm='2018-10-05',
        alkamis_pvm='2018-10-05',
        paattymis_pvm=None,
        changed_by=tester4_user
    )

    vakasuhde_1 = Varhaiskasvatussuhde.objects.create(
        toimipaikka=toimipaikka_1,
        varhaiskasvatuspaatos=vakapaatos_1,
        alkamis_pvm='2017-02-11',
        paattymis_pvm='2018-02-24',
        changed_by=tester_user
    )

    vakasuhde_2 = Varhaiskasvatussuhde.objects.create(
        toimipaikka=toimipaikka_1,
        varhaiskasvatuspaatos=vakapaatos_2,
        alkamis_pvm='2018-09-05',
        paattymis_pvm=None,
        changed_by=tester_user
    )

    vakasuhde_3 = Varhaiskasvatussuhde.objects.create(
        toimipaikka=toimipaikka_2,
        varhaiskasvatuspaatos=vakapaatos_3,
        alkamis_pvm='2018-09-05',
        paattymis_pvm=None,
        changed_by=tester2_user
    )

    vakasuhde_4 = Varhaiskasvatussuhde.objects.create(
        toimipaikka=toimipaikka_5,
        varhaiskasvatuspaatos=vakapaatos_4,
        alkamis_pvm='2018-09-05',
        paattymis_pvm=None,
        changed_by=tester2_user
    )

    vakasuhde_5 = Varhaiskasvatussuhde.objects.create(
        toimipaikka=toimipaikka_5,
        varhaiskasvatuspaatos=vakapaatos_5,
        alkamis_pvm='2018-09-05',
        paattymis_pvm=None,
        changed_by=tester4_user
    )

    vakasuhde_6 = Varhaiskasvatussuhde.objects.create(
        toimipaikka=toimipaikka_2,
        varhaiskasvatuspaatos=vakapaatos_6,
        alkamis_pvm="2018-02-11",
        paattymis_pvm="2019-02-24",
        changed_by=tester_user
    )

    vakasuhde_7 = Varhaiskasvatussuhde.objects.create(
        toimipaikka=toimipaikka_4,
        varhaiskasvatuspaatos=vakapaatos_7,
        alkamis_pvm='2018-09-05',
        paattymis_pvm='2019-04-20',
        changed_by=tester2_user
    )

    vakasuhde_8 = Varhaiskasvatussuhde.objects.create(
        toimipaikka=toimipaikka_1,
        varhaiskasvatuspaatos=vakapaatos_7,
        alkamis_pvm='2018-05-01',
        paattymis_pvm='2019-10-24',
        changed_by=tester2_user
    )

    vakasuhde_9 = Varhaiskasvatussuhde.objects.create(
        toimipaikka=toimipaikka_5,
        varhaiskasvatuspaatos=vakapaatos_9,
        alkamis_pvm='2019-11-11',
        paattymis_pvm=None,
        changed_by=tester2_user
    )

    assign_object_level_permissions(toimipaikka_1_organisaatio_oid, Lapsi, lapsi_1)
    assign_object_level_permissions(toimipaikka_1_organisaatio_oid, Varhaiskasvatuspaatos, vakapaatos_1)
    assign_object_level_permissions(toimipaikka_1_organisaatio_oid, Varhaiskasvatussuhde, vakasuhde_1)
    assign_object_level_permissions(toimipaikka_1_organisaatio_oid, Lapsi, lapsi_2)
    assign_object_level_permissions(toimipaikka_1_organisaatio_oid, Varhaiskasvatuspaatos, vakapaatos_2)
    assign_object_level_permissions(toimipaikka_1_organisaatio_oid, Varhaiskasvatussuhde, vakasuhde_2)

    assign_object_level_permissions(vakajarjestaja_2_organisaatio_oid, Lapsi, lapsi_1)
    assign_object_level_permissions(vakajarjestaja_2_organisaatio_oid, Varhaiskasvatuspaatos, vakapaatos_1)
    assign_object_level_permissions(vakajarjestaja_2_organisaatio_oid, Varhaiskasvatussuhde, vakasuhde_1)
    assign_object_level_permissions(vakajarjestaja_2_organisaatio_oid, Lapsi, lapsi_2)
    assign_object_level_permissions(vakajarjestaja_2_organisaatio_oid, Varhaiskasvatuspaatos, vakapaatos_2)
    assign_object_level_permissions(vakajarjestaja_2_organisaatio_oid, Varhaiskasvatussuhde, vakasuhde_2)

    assign_object_level_permissions(vakajarjestaja_1_organisaatio_oid, Lapsi, lapsi_3)
    assign_object_level_permissions(vakajarjestaja_1_organisaatio_oid, Varhaiskasvatuspaatos, vakapaatos_3)
    assign_object_level_permissions(vakajarjestaja_1_organisaatio_oid, Varhaiskasvatussuhde, vakasuhde_3)

    assign_vakajarjestaja_lapsi_paos_permissions(vakajarjestaja_1_organisaatio_oid, vakajarjestaja_2_organisaatio_oid,
                                                 vakajarjestaja_1_organisaatio_oid, lapsi_4)
    assign_vakajarjestaja_vakatiedot_paos_permissions(vakajarjestaja_1_organisaatio_oid, vakajarjestaja_2_organisaatio_oid,
                                                      vakajarjestaja_1_organisaatio_oid, Varhaiskasvatuspaatos, vakapaatos_4)
    assign_vakajarjestaja_vakatiedot_paos_permissions(vakajarjestaja_1_organisaatio_oid, vakajarjestaja_2_organisaatio_oid,
                                                      vakajarjestaja_1_organisaatio_oid, Varhaiskasvatussuhde, vakasuhde_4)

    assign_toimipaikka_lapsi_paos_permissions(toimipaikka_5_organisaatio_oid, vakajarjestaja_1_organisaatio_oid, lapsi_4)
    assign_toimipaikka_vakatiedot_paos_permissions(toimipaikka_5_organisaatio_oid, vakajarjestaja_1_organisaatio_oid,
                                                   Varhaiskasvatuspaatos, vakapaatos_4)
    assign_toimipaikka_vakatiedot_paos_permissions(toimipaikka_5_organisaatio_oid, vakajarjestaja_1_organisaatio_oid,
                                                   Varhaiskasvatussuhde, vakasuhde_4)

    assign_vakajarjestaja_lapsi_paos_permissions(vakajarjestaja_4_organisaatio_oid, vakajarjestaja_2_organisaatio_oid,
                                                 vakajarjestaja_4_organisaatio_oid, lapsi_5)
    assign_vakajarjestaja_vakatiedot_paos_permissions(vakajarjestaja_4_organisaatio_oid, vakajarjestaja_2_organisaatio_oid,
                                                      vakajarjestaja_4_organisaatio_oid, Varhaiskasvatuspaatos, vakapaatos_5)
    assign_vakajarjestaja_vakatiedot_paos_permissions(vakajarjestaja_4_organisaatio_oid, vakajarjestaja_2_organisaatio_oid,
                                                      vakajarjestaja_4_organisaatio_oid, Varhaiskasvatussuhde, vakasuhde_5)

    assign_toimipaikka_lapsi_paos_permissions(toimipaikka_5_organisaatio_oid, vakajarjestaja_4_organisaatio_oid,
                                              lapsi_5)
    assign_toimipaikka_vakatiedot_paos_permissions(toimipaikka_5_organisaatio_oid, vakajarjestaja_4_organisaatio_oid,
                                                   Varhaiskasvatuspaatos, vakapaatos_5)
    assign_toimipaikka_vakatiedot_paos_permissions(toimipaikka_5_organisaatio_oid, vakajarjestaja_4_organisaatio_oid,
                                                   Varhaiskasvatussuhde, vakasuhde_5)

    assign_object_level_permissions(toimipaikka_2_organisaatio_oid, Lapsi, lapsi_6)
    assign_object_level_permissions(vakajarjestaja_1_organisaatio_oid, Lapsi, lapsi_6)
    assign_object_level_permissions(toimipaikka_2_organisaatio_oid, Varhaiskasvatuspaatos, vakapaatos_6)
    assign_object_level_permissions(toimipaikka_2_organisaatio_oid, Varhaiskasvatussuhde, vakasuhde_6)
    assign_object_level_permissions(vakajarjestaja_1_organisaatio_oid, Varhaiskasvatuspaatos, vakapaatos_6)
    assign_object_level_permissions(vakajarjestaja_1_organisaatio_oid, Varhaiskasvatussuhde, vakasuhde_6)

    assign_object_level_permissions(toimipaikka_1_organisaatio_oid, Lapsi, lapsi_7)
    assign_object_level_permissions(toimipaikka_4_organisaatio_oid, Lapsi, lapsi_7)
    assign_object_level_permissions(vakajarjestaja_2_organisaatio_oid, Lapsi, lapsi_7)
    assign_object_level_permissions(vakajarjestaja_2_organisaatio_oid, Varhaiskasvatuspaatos, vakapaatos_7)
    assign_object_level_permissions(vakajarjestaja_2_organisaatio_oid, Varhaiskasvatuspaatos, vakapaatos_8)
    assign_object_level_permissions(toimipaikka_1_organisaatio_oid, Varhaiskasvatuspaatos, vakapaatos_7)
    assign_object_level_permissions(vakajarjestaja_2_organisaatio_oid, Varhaiskasvatussuhde, vakasuhde_7)
    assign_object_level_permissions(toimipaikka_1_organisaatio_oid, Varhaiskasvatussuhde, vakasuhde_7)
    assign_object_level_permissions(toimipaikka_1_organisaatio_oid, Varhaiskasvatussuhde, vakasuhde_8)
    assign_object_level_permissions(vakajarjestaja_2_organisaatio_oid, Varhaiskasvatussuhde, vakasuhde_8)

    assign_vakajarjestaja_lapsi_paos_permissions(vakajarjestaja_1_organisaatio_oid, vakajarjestaja_2_organisaatio_oid,
                                                 vakajarjestaja_1_organisaatio_oid, lapsi_8)
    assign_vakajarjestaja_vakatiedot_paos_permissions(vakajarjestaja_1_organisaatio_oid, vakajarjestaja_2_organisaatio_oid,
                                                      vakajarjestaja_1_organisaatio_oid, Varhaiskasvatuspaatos, vakapaatos_9)
    assign_vakajarjestaja_vakatiedot_paos_permissions(vakajarjestaja_1_organisaatio_oid, vakajarjestaja_2_organisaatio_oid,
                                                      vakajarjestaja_1_organisaatio_oid, Varhaiskasvatussuhde, vakasuhde_9)

    assign_toimipaikka_lapsi_paos_permissions(toimipaikka_5_organisaatio_oid, vakajarjestaja_1_organisaatio_oid, lapsi_8)
    assign_toimipaikka_vakatiedot_paos_permissions(toimipaikka_5_organisaatio_oid, vakajarjestaja_1_organisaatio_oid,
                                                   Varhaiskasvatuspaatos, vakapaatos_9)
    assign_toimipaikka_vakatiedot_paos_permissions(toimipaikka_5_organisaatio_oid, vakajarjestaja_1_organisaatio_oid,
                                                   Varhaiskasvatussuhde, vakasuhde_9)


def create_huoltajat():
    from django.contrib.auth.models import User
    from varda.misc import hash_string
    from varda.models import Henkilo, Huoltaja

    tester_user = User.objects.get(username='tester')

    henkilo_huoltaja_1 = Henkilo.objects.get(henkilotunnus_unique_hash=hash_string('020476-321F'))
    henkilo_huoltaja_2 = Henkilo.objects.get(henkilotunnus_unique_hash=hash_string('120386-109V'))
    henkilo_huoltaja_3 = Henkilo.objects.get(henkilotunnus_unique_hash=hash_string('110548-316P'))
    henkilo_huoltaja_4 = Henkilo.objects.get(henkilotunnus_unique_hash=hash_string('291090-398U'))

    henkilo_huoltaja_suomifi = Henkilo.objects.get(henkilotunnus_unique_hash=hash_string('010280-952L'))

    Huoltaja.objects.create(
        henkilo=henkilo_huoltaja_1,
        changed_by=tester_user
    )

    Huoltaja.objects.create(
        henkilo=henkilo_huoltaja_2,
        changed_by=tester_user
    )

    Huoltaja.objects.create(
        henkilo=henkilo_huoltaja_3,
        changed_by=tester_user
    )

    Huoltaja.objects.create(
        henkilo=henkilo_huoltaja_4,
        changed_by=tester_user
    )

    Huoltaja.objects.create(
        henkilo=henkilo_huoltaja_suomifi,
        changed_by=tester_user
    )


def create_huoltajuussuhteet():
    from django.contrib.auth.models import User
    from varda.misc import hash_string
    from varda.models import Henkilo, Huoltaja, Huoltajuussuhde, Lapsi

    admin_user = User.objects.get(username='credadmin')

    henkilo_lapsi_1 = Henkilo.objects.get(henkilotunnus_unique_hash=hash_string('010114A0013'))
    henkilo_lapsi_2 = Henkilo.objects.get(henkilotunnus_unique_hash=hash_string('120516A123V'))
    henkilo_lapsi_3 = Henkilo.objects.get(henkilotunnus_unique_hash=hash_string('170334-130B'))
    henkilo_lapsi_4 = Henkilo.objects.get(henkilotunnus_unique_hash=hash_string('120699-985W'))
    henkilo_lapsi_5 = Henkilo.objects.get(henkilotunnus_unique_hash=hash_string('220616A322J'))
    henkilo_lapsi_6 = Henkilo.objects.get(henkilotunnus_unique_hash=hash_string('010215A951T'))

    lapsi_1 = Lapsi.objects.filter(henkilo=henkilo_lapsi_1).first()
    lapsi_2 = Lapsi.objects.filter(henkilo=henkilo_lapsi_2).first()
    lapsi_3 = Lapsi.objects.filter(henkilo=henkilo_lapsi_3).first()
    lapsi_4 = Lapsi.objects.filter(henkilo=henkilo_lapsi_4).first()
    lapsi_5 = Lapsi.objects.filter(henkilo=henkilo_lapsi_5).first()
    lapsi_6 = Lapsi.objects.filter(henkilo=henkilo_lapsi_6)[0]
    lapsi_7 = Lapsi.objects.filter(henkilo=henkilo_lapsi_6)[1]
    lapsi_8 = Lapsi.objects.filter(henkilo=henkilo_lapsi_6)[2]

    henkilo_huoltaja_1 = Henkilo.objects.get(henkilotunnus_unique_hash=hash_string('020476-321F'))
    henkilo_huoltaja_2 = Henkilo.objects.get(henkilotunnus_unique_hash=hash_string('120386-109V'))
    henkilo_huoltaja_3 = Henkilo.objects.get(henkilotunnus_unique_hash=hash_string('110548-316P'))
    henkilo_huoltaja_4 = Henkilo.objects.get(henkilotunnus_unique_hash=hash_string('291090-398U'))

    huoltaja_1 = Huoltaja.objects.filter(henkilo=henkilo_huoltaja_1).first()
    huoltaja_2 = Huoltaja.objects.filter(henkilo=henkilo_huoltaja_2).first()
    huoltaja_3 = Huoltaja.objects.filter(henkilo=henkilo_huoltaja_3).first()
    huoltaja_4 = Huoltaja.objects.filter(henkilo=henkilo_huoltaja_4).first()

    henkilo_huoltaja_suomifi = Henkilo.objects.get(henkilotunnus_unique_hash=hash_string('010280-952L'))
    huoltaja_suomifi = Huoltaja.objects.filter(henkilo=henkilo_huoltaja_suomifi).first()

    Huoltajuussuhde.objects.create(
        huoltaja=huoltaja_1,
        lapsi=lapsi_1,
        voimassa_kytkin=True,
        changed_by_id=admin_user.id
    )

    Huoltajuussuhde.objects.create(
        huoltaja=huoltaja_2,
        lapsi=lapsi_1,
        voimassa_kytkin=True,
        changed_by_id=admin_user.id
    )

    Huoltajuussuhde.objects.create(
        huoltaja=huoltaja_2,
        lapsi=lapsi_2,
        voimassa_kytkin=True,
        changed_by_id=admin_user.id
    )

    Huoltajuussuhde.objects.create(
        huoltaja=huoltaja_2,
        lapsi=lapsi_3,
        voimassa_kytkin=True,
        changed_by_id=admin_user.id
    )

    Huoltajuussuhde.objects.create(
        huoltaja=huoltaja_3,
        lapsi=lapsi_4,
        voimassa_kytkin=True,
        changed_by_id=admin_user.id
    )

    Huoltajuussuhde.objects.create(
        huoltaja=huoltaja_4,
        lapsi=lapsi_5,
        voimassa_kytkin=True,
        changed_by_id=admin_user.id
    )

    Huoltajuussuhde.objects.create(
        huoltaja=huoltaja_suomifi,
        lapsi=lapsi_6,
        voimassa_kytkin=True,
        changed_by_id=admin_user.id
    )

    Huoltajuussuhde.objects.create(
        huoltaja=huoltaja_suomifi,
        lapsi=lapsi_7,
        voimassa_kytkin=True,
        changed_by_id=admin_user.id
    )

    Huoltajuussuhde.objects.create(
        huoltaja=huoltaja_suomifi,
        lapsi=lapsi_8,
        voimassa_kytkin=True,
        changed_by_id=admin_user.id
    )


def create_maksutiedot():
    from django.contrib.auth.models import Group, User
    from guardian.shortcuts import assign_perm
    from varda.models import Maksutieto, Huoltajuussuhde
    from varda.permission_groups import (assign_vakajarjestaja_maksutieto_paos_permissions,
                                         assign_toimipaikka_maksutieto_paos_permissions)

    tester_user = User.objects.get(username='tester')
    tester2_user = User.objects.get(username='tester2')
    tester4_user = User.objects.get(username='tester4')
    group_tester = Group.objects.get(name='HUOLTAJATIETO_TALLENNUS_1.2.246.562.10.9395737548810')
    group_tester2 = Group.objects.get(name='HUOLTAJATIETO_TALLENNUS_1.2.246.562.10.34683023489')
    group_tester4 = Group.objects.get(name='HUOLTAJATIETO_TALLENNUS_1.2.246.562.10.93957375484')

    vakajarjestaja_2_organisaatio_oid = '1.2.246.562.10.93957375488'
    vakajarjestaja_4_organisaatio_oid = '1.2.246.562.10.93957375484'

    toimipaikka_5_organisaatio_oid = '1.2.246.562.10.9395737548817'

    mp1 = Maksutieto.objects.create(
        yksityinen_jarjestaja=False,
        maksun_peruste_koodi='mp01',
        palveluseteli_arvo=0.00,
        asiakasmaksu=0.00,
        perheen_koko=3,
        alkamis_pvm='2019-09-01',
        changed_by=tester_user
    )
    assign_perm('view_maksutieto', group_tester, mp1)
    assign_perm('change_maksutieto', group_tester, mp1)
    assign_perm('delete_maksutieto', group_tester, mp1)
    Huoltajuussuhde.objects.get(pk=1).maksutiedot.add(mp1)

    mp2 = Maksutieto.objects.create(
        yksityinen_jarjestaja=False,
        maksun_peruste_koodi='mp02',
        palveluseteli_arvo=150,
        asiakasmaksu=0,
        perheen_koko=3,
        alkamis_pvm='2019-09-01',
        paattymis_pvm='2025-01-01',
        changed_by=tester2_user
    )
    assign_perm('view_maksutieto', group_tester2, mp2)
    assign_perm('change_maksutieto', group_tester2, mp2)
    assign_perm('delete_maksutieto', group_tester2, mp2)
    Huoltajuussuhde.objects.get(pk=4).maksutiedot.add(mp2)

    mp3 = Maksutieto.objects.create(
        yksityinen_jarjestaja=False,
        maksun_peruste_koodi='mp03',
        palveluseteli_arvo=100,
        asiakasmaksu=150,
        perheen_koko=2,
        alkamis_pvm='2019-09-01',
        changed_by=tester_user
    )
    assign_perm('view_maksutieto', group_tester, mp3)
    assign_perm('change_maksutieto', group_tester, mp3)
    assign_perm('delete_maksutieto', group_tester, mp3)
    Huoltajuussuhde.objects.get(pk=2).maksutiedot.add(mp3, mp1)

    mp4 = Maksutieto.objects.create(
        yksityinen_jarjestaja=False,
        maksun_peruste_koodi='mp03',
        palveluseteli_arvo=100,
        asiakasmaksu=150,
        perheen_koko=2,
        alkamis_pvm='2019-09-01',
        changed_by=tester4_user
    )
    assign_perm('view_maksutieto', group_tester4, mp4)
    assign_perm('change_maksutieto', group_tester4, mp4)
    assign_perm('delete_maksutieto', group_tester4, mp4)
    Huoltajuussuhde.objects.get(pk=6).maksutiedot.add(mp4)

    assign_vakajarjestaja_maksutieto_paos_permissions(vakajarjestaja_4_organisaatio_oid, vakajarjestaja_2_organisaatio_oid, mp4)
    assign_toimipaikka_maksutieto_paos_permissions(toimipaikka_5_organisaatio_oid, vakajarjestaja_4_organisaatio_oid, mp4)


def create_paos_toiminta():
    from django.contrib.auth.models import Group
    from guardian.shortcuts import assign_perm
    from varda.models import PaosToiminta, VakaJarjestaja, User, Toimipaikka
    from varda import permissions

    vakajarjestaja_1 = VakaJarjestaja.objects.get(id=1)
    vakajarjestaja_2 = VakaJarjestaja.objects.get(id=2)
    vakajarjestaja_4 = VakaJarjestaja.objects.get(id=4)
    toimipaikka_5_under_vakajarjestaja_2 = Toimipaikka.objects.get(id=5)
    toimipaikka_6_under_vakajarjestaja_4 = Toimipaikka.objects.get(id=6)
    tester3_user = User.objects.get(username='tester3')
    tester4_user = User.objects.get(username='tester4')
    tester_e2e_user = User.objects.get(username='tester-e2e')
    group_paakayttaja_vakajarjestaja_1 = Group.objects.get(name='VARDA-PAAKAYTTAJA_1.2.246.562.10.34683023489')
    group_paakayttaja_vakajarjestaja_4 = Group.objects.get(name='VARDA-PAAKAYTTAJA_1.2.246.562.10.93957375484')

    """
    Toimipaikka_5 and toimipaikka_6 have identical names, but they are under different vakajarjestajat.
    """

    # vakajarjestaja_2 gives permission to vakajarjestaja_1 to add lapset under their toimipaikat
    paos_toiminta_1 = PaosToiminta.objects.create(
        oma_organisaatio=vakajarjestaja_2,
        paos_organisaatio=vakajarjestaja_1,
        voimassa_kytkin=True,
        changed_by=tester3_user
    )

    # vakajarjestaja_1 takes toimipaikka_5 in use for PAOS-lapset
    paos_toiminta_2 = PaosToiminta.objects.create(
        oma_organisaatio=vakajarjestaja_1,
        paos_toimipaikka=toimipaikka_5_under_vakajarjestaja_2,
        voimassa_kytkin=True,
        changed_by=tester4_user
    )

    assign_perm('view_paostoiminta', tester3_user, paos_toiminta_1)
    assign_perm('delete_paostoiminta', tester3_user, paos_toiminta_1)
    assign_perm('view_paostoiminta', tester4_user, paos_toiminta_2)
    assign_perm('delete_paostoiminta', tester4_user, paos_toiminta_2)
    permissions.assign_object_level_permissions(vakajarjestaja_1.organisaatio_oid, Toimipaikka,
                                                toimipaikka_5_under_vakajarjestaja_2, paos_kytkin=True)

    # vakajarjestaja_4 gives permission to vakajarjestaja_1 to add lapset under their toimipaikat
    paos_toiminta_3 = PaosToiminta.objects.create(
        oma_organisaatio=vakajarjestaja_4,
        paos_organisaatio=vakajarjestaja_1,
        voimassa_kytkin=True,
        changed_by=tester_e2e_user
    )

    # vakajarjestaja_1 takes toimipaikka_6 in use for PAOS-lapset
    paos_toiminta_4 = PaosToiminta.objects.create(
        oma_organisaatio=vakajarjestaja_1,
        paos_toimipaikka=toimipaikka_6_under_vakajarjestaja_4,
        voimassa_kytkin=True,
        changed_by=tester4_user
    )

    assign_perm('view_paostoiminta', group_paakayttaja_vakajarjestaja_4, paos_toiminta_3)
    assign_perm('delete_paostoiminta', group_paakayttaja_vakajarjestaja_4, paos_toiminta_3)
    assign_perm('view_paostoiminta', group_paakayttaja_vakajarjestaja_1, paos_toiminta_4)
    assign_perm('delete_paostoiminta', group_paakayttaja_vakajarjestaja_1, paos_toiminta_4)
    permissions.assign_object_level_permissions(vakajarjestaja_1.organisaatio_oid, Toimipaikka, toimipaikka_6_under_vakajarjestaja_4, paos_kytkin=True)

    # vakajarjestaja_2 gives permission to vakajarjestaja_4 to add lapset under their toimipaikat
    paos_toiminta_3 = PaosToiminta.objects.create(
        oma_organisaatio=vakajarjestaja_2,
        paos_organisaatio=vakajarjestaja_4,
        voimassa_kytkin=True,
        changed_by=tester3_user
    )

    # vakajarjestaja_4 takes toimipaikka_5 in use for PAOS-lapset
    paos_toiminta_4 = PaosToiminta.objects.create(
        oma_organisaatio=vakajarjestaja_4,
        paos_toimipaikka=toimipaikka_5_under_vakajarjestaja_2,
        voimassa_kytkin=True,
        changed_by=tester4_user
    )

    assign_perm('view_paostoiminta', tester3_user, paos_toiminta_3)
    assign_perm('delete_paostoiminta', tester3_user, paos_toiminta_3)
    assign_perm('view_paostoiminta', tester4_user, paos_toiminta_4)
    assign_perm('delete_paostoiminta', tester4_user, paos_toiminta_4)
    permissions.assign_object_level_permissions(vakajarjestaja_1.organisaatio_oid, Toimipaikka,
                                                toimipaikka_5_under_vakajarjestaja_2, paos_kytkin=True)


def create_paos_oikeus():
    from django.contrib.auth.models import Group
    from guardian.shortcuts import assign_perm
    from varda.models import PaosOikeus, VakaJarjestaja, User
    from varda.permissions import change_paos_tallentaja_organization

    vakajarjestaja_1 = VakaJarjestaja.objects.get(id=1)
    vakajarjestaja_2 = VakaJarjestaja.objects.get(id=2)
    vakajarjestaja_4 = VakaJarjestaja.objects.get(id=4)
    tester3_user = User.objects.get(username='tester3')
    tester4_user = User.objects.get(username='tester4')
    group_paakayttaja_vakajarjestaja_1 = Group.objects.get(name='VARDA-PAAKAYTTAJA_1.2.246.562.10.34683023489')
    group_paakayttaja_vakajarjestaja_4 = Group.objects.get(name='VARDA-PAAKAYTTAJA_1.2.246.562.10.93957375484')

    """
    vakajarjestaja_1 <--> vakajarjestaja_2
    """
    paos_oikeus_1 = PaosOikeus.objects.create(
        jarjestaja_kunta_organisaatio=vakajarjestaja_1,
        tuottaja_organisaatio=vakajarjestaja_2,
        voimassa_kytkin=True,
        tallentaja_organisaatio=vakajarjestaja_1,
        changed_by=tester4_user
    )

    assign_perm('view_paosoikeus', tester3_user, paos_oikeus_1)
    assign_perm('view_paosoikeus', tester4_user, paos_oikeus_1)
    assign_perm('change_paosoikeus', tester4_user, paos_oikeus_1)

    """
    vakajarjestaja_1 <--> vakajarjestaja_4
    """
    paos_oikeus_2 = PaosOikeus.objects.create(
        jarjestaja_kunta_organisaatio=vakajarjestaja_1,
        tuottaja_organisaatio=vakajarjestaja_4,
        voimassa_kytkin=True,
        tallentaja_organisaatio=vakajarjestaja_1,
        changed_by=tester4_user
    )

    assign_perm('view_paosoikeus', group_paakayttaja_vakajarjestaja_4, paos_oikeus_2)
    assign_perm('view_paosoikeus', group_paakayttaja_vakajarjestaja_1, paos_oikeus_2)
    assign_perm('change_paosoikeus', group_paakayttaja_vakajarjestaja_1, paos_oikeus_2)

    jarjestaja_kunta_organisaatio_id = 1
    tuottaja_organisaatio_id = 2
    tallentaja_organisaatio_id = 1
    voimassa_kytkin = True

    change_paos_tallentaja_organization(jarjestaja_kunta_organisaatio_id, tuottaja_organisaatio_id,
                                        tallentaja_organisaatio_id, voimassa_kytkin)

    """
    vakajarjestaja_4 <--> vakajarjestaja_2
    """
    paos_oikeus_2 = PaosOikeus.objects.create(
        jarjestaja_kunta_organisaatio=vakajarjestaja_4,
        tuottaja_organisaatio=vakajarjestaja_2,
        voimassa_kytkin=True,
        tallentaja_organisaatio=vakajarjestaja_4,
        changed_by=tester4_user
    )

    assign_perm('view_paosoikeus', tester3_user, paos_oikeus_2)
    assign_perm('view_paosoikeus', tester4_user, paos_oikeus_2)
    assign_perm('change_paosoikeus', tester4_user, paos_oikeus_2)


def create_user_data():
    from django.contrib.auth.models import User
    from varda.models import Z3_AdditionalCasUserFields, Z4_CasKayttoOikeudet

    tester_user = User.objects.get(username='tester')
    tester2_user = User.objects.get(username='tester2')
    tester6_user = User.objects.get(username='tester6')
    tester7_user = User.objects.get(username='tester7')
    tester9_user = User.objects.get(username='tester9')

    pk_vakajarjestaja_1_user = User.objects.get(username='pkvakajarjestaja1')
    pk_vakajarjestaja_2_user = User.objects.get(username='pkvakajarjestaja2')

    Z3_AdditionalCasUserFields.objects.create(
        user_id=tester_user.id,
        kayttajatyyppi='VIRKAILIJA',
        henkilo_oid='1.2.345678910',
        asiointikieli_koodi='sv',
        approved_oph_staff=False,
        last_modified='2019-01-24 12:00:00+1459'
    )

    Z3_AdditionalCasUserFields.objects.create(
        user_id=tester2_user.id,
        kayttajatyyppi='VIRKAILIJA',
        henkilo_oid='1.2.345678911',
        asiointikieli_koodi='fi',
        approved_oph_staff=False,
        last_modified='2019-01-24 12:00:00+1459'
    )

    Z3_AdditionalCasUserFields.objects.create(
        user_id=tester6_user.id,
        kayttajatyyppi='VIRKAILIJA',
        henkilo_oid='1.2.345678001',
        asiointikieli_koodi='fi',
        approved_oph_staff=False,
        last_modified='2019-01-24 12:00:00+1459'
    )

    Z3_AdditionalCasUserFields.objects.create(
        user_id=tester7_user.id,
        kayttajatyyppi='VIRKAILIJA',
        henkilo_oid='1.2.345679001',
        asiointikieli_koodi='fi',
        approved_oph_staff=False,
        last_modified='2019-01-24 12:00:00+1459'
    )

    Z3_AdditionalCasUserFields.objects.create(
        user_id=tester9_user.id,
        kayttajatyyppi='VIRKAILIJA',
        henkilo_oid='1.2.345680001',
        asiointikieli_koodi='fi',
        approved_oph_staff=False,
        last_modified='2019-01-24 12:00:00+1459'
    )

    Z3_AdditionalCasUserFields.objects.create(
        user_id=pk_vakajarjestaja_1_user.id,
        kayttajatyyppi='PALVELU',
        henkilo_oid='',
        asiointikieli_koodi='fi',
        approved_oph_staff=False,
        last_modified='2019-01-24 12:00:00+1459'
    )

    Z3_AdditionalCasUserFields.objects.create(
        user_id=pk_vakajarjestaja_2_user.id,
        kayttajatyyppi='PALVELU',
        henkilo_oid='',
        asiointikieli_koodi='fi',
        approved_oph_staff=False,
        last_modified='2019-01-24 12:00:00+1459'
    )

    Z4_CasKayttoOikeudet.objects.create(
        user_id=tester2_user.id,
        organisaatio_oid='1.2.246.562.10.34683023489',
        kayttooikeus='VARDA-TALLENTAJA',
        last_modified='2019-01-24 12:00:00+1459'
    )


def create_koodisto_data():
    from varda.models import Z2_Koodisto, Z2_Code, Z2_CodeTranslation
    from varda import koodistopalvelu

    koodisto_codes = {
        'kunta_koodit': ['005', '009', '010', '016', '018', '019', '020', '035', '043', '046', '047', '049', '050',
                         '051', '052', '060', '061', '062', '065', '069', '071', '072', '074', '075', '076', '077',
                         '078', '079', '081', '082', '086', '090', '091', '092', '097', '098', '099', '102', '103',
                         '105', '106', '108', '109', '111', '139', '140', '142', '143', '145', '146', '148', '149',
                         '151', '152', '153', '165', '167', '169', '170', '171', '172', '176', '177', '178', '179',
                         '181', '182', '186', '202', '204', '205', '208', '211', '213', '214', '216', '217', '218',
                         '224', '226', '230', '231', '232', '233', '235', '236', '239', '240', '241', '244', '245',
                         '249', '250', '256', '257', '260', '261', '263', '265', '271', '272', '273', '275', '276',
                         '280', '284', '285', '286', '287', '288', '290', '291', '295', '297', '300', '301', '304',
                         '305', '309', '312', '316', '317', '318', '320', '322', '398', '399', '400', '402', '403',
                         '405', '407', '408', '410', '416', '417', '418', '420', '421', '422', '423', '425', '426',
                         '430', '433', '434', '435', '436', '438', '440', '441', '444', '445', '475', '478', '480',
                         '481', '483', '484', '489', '491', '494', '495', '498', '499', '500', '503', '504', '505',
                         '507', '508', '529', '531', '535', '536', '538', '541', '543', '545', '560', '561', '562',
                         '563', '564', '576', '577', '578', '580', '581', '583', '584', '588', '592', '593', '595',
                         '598', '599', '601', '604', '607', '608', '609', '611', '614', '615', '616', '619', '620',
                         '623', '624', '625', '626', '630', '631', '635', '636', '638', '678', '680', '681', '683',
                         '684', '686', '687', '689', '691', '694', '697', '698', '700', '702', '704', '707', '710',
                         '729', '732', '734', '736', '738', '739', '740', '742', '743', '746', '747', '748', '749',
                         '751', '753', '755', '758', '759', '761', '762', '765', '766', '768', '771', '777', '778',
                         '781', '783', '785', '790', '791', '831', '832', '833', '834', '837', '844', '845', '846',
                         '848', '849', '850', '851', '853', '854', '857', '858', '859', '886', '887', '889', '890',
                         '892', '893', '895', '905', '908', '911', '915', '918', '921', '922', '924', '925', '927',
                         '931', '934', '935', '936', '941', '946', '976', '977', '980', '981', '989', '992'],
        'kieli_koodit': ['99', 'AA', 'AB', 'AE', 'AF', 'AK', 'AM', 'AN', 'AR', 'AS', 'AV', 'AY', 'AZ', 'BA', 'BE', 'BG',
                         'BH', 'BI', 'BM', 'BN', 'BO', 'BR', 'BS', 'CA', 'CE', 'CH', 'CO', 'CR', 'CS', 'CU', 'CV', 'CY',
                         'DA', 'DE', 'DR', 'DV', 'DZ', 'EE', 'EL', 'EN', 'EO', 'ES', 'ET', 'EU', 'FA', 'FF', 'FI', 'FJ',
                         'FO', 'FR', 'FY', 'GA', 'GD', 'GG', 'GL', 'GN', 'GU', 'GV', 'HA', 'HE', 'HI', 'HO', 'HR', 'HT',
                         'HU', 'HY', 'HZ', 'IA', 'ID', 'IE', 'IG', 'II', 'IK', 'IM', 'IO', 'IS', 'IT', 'IU', 'IW', 'JA',
                         'JE', 'JV', 'KA', 'KE', 'KG', 'KI', 'KJ', 'KK', 'KL', 'KM', 'KN', 'KO', 'KR', 'KS', 'KU', 'KV',
                         'KW', 'KY', 'LA', 'LB', 'LG', 'LI', 'LN', 'LO', 'LT', 'LU', 'LV', 'MG', 'MH', 'MI', 'MK', 'ML',
                         'MN', 'MO', 'MR', 'MS', 'MT', 'MY', 'NA', 'NB', 'ND', 'NE', 'NG', 'NL', 'NN', 'NO', 'NR', 'NV',
                         'NY', 'OC', 'OJ', 'OM', 'OR', 'OS', 'PA', 'PI', 'PL', 'PS', 'PT', 'QU', 'RI', 'RM', 'RN', 'RO',
                         'RU', 'RW', 'SA', 'SC', 'SD', 'SEIN', 'SEKO', 'SEPO', 'SG', 'SH', 'SI', 'SK', 'SL', 'SM', 'SN',
                         'SO', 'SQ', 'SR', 'SS', 'ST', 'SU', 'SV', 'SW', 'TA', 'TE', 'TG', 'TH', 'TI', 'TK', 'TL', 'TN',
                         'TO', 'TR', 'TS', 'TT', 'TW', 'TY', 'UG', 'UK', 'UR', 'UZ', 'WA', 'VE', 'VI', 'VK', 'VO', 'WO',
                         'XH', 'XX', 'YI', 'YO', 'ZA', 'ZH', 'ZU'],
        'jarjestamismuoto_koodit': ['jm01', 'jm02', 'jm03', 'jm04', 'jm05'],
        'toimintamuoto_koodit': ['tm01', 'tm02', 'tm03'],
        'kasvatusopillinen_jarjestelma_koodit': ['kj01', 'kj02', 'kj03', 'kj04', 'kj05', 'kj98', 'kj99'],
        'toiminnallinen_painotus_koodit': ['tp01', 'tp02', 'tp03', 'tp04', 'tp05', 'tp06', 'tp07', 'tp08', 'tp09',
                                           'tp98', 'tp99'],
        'tyosuhde_koodit': ['1', '2'],
        'tyoaika_koodit': ['1', '2'],
        'tehtavanimike_koodit': ['39407', '41712', '43525', '64212', '77826', '81787', '84053', '84724'],
        'sukupuoli_koodit': ['1', '2', '-1'],
        'tutkinto_koodit': ['001', '002', '003', '321901', '371101', '371168', '371169', '374114', '381204', '381241',
                            '384246', '511501', '571201', '571254', '612101', '612102', '612103', '612104', '612105',
                            '612107', '612108', '612199', '612201', '612202', '612203', '612204', '612205', '612299',
                            '612999', '613101', '613201', '613352', '613353', '613354', '613355', '613356', '613357',
                            '613399', '613401', '613402', '613501', '613652', '613952', '613999', '671201', '712101',
                            '712102', '712104', '712105', '712108', '712109', '712199', '712201', '712202', '712203',
                            '712204', '712205', '712299', '719951', '719999', '771301', '812101', '812102', '812103',
                            '815101', '815102', '815103'],
        'maksun_peruste_koodit': ['mp01', 'mp02', 'mp03'],
        'lahdejarjestelma_koodit': ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15']
    }

    update_datetime = datetime.datetime.strptime('2020-05-14', '%Y-%m-%d')
    update_datetime = update_datetime.replace(tzinfo=datetime.timezone.utc)

    for key, value in koodistopalvelu.KOODISTOPALVELU_DICT.items():
        koodisto_obj = Z2_Koodisto.objects.create(name=key.value,
                                                  name_koodistopalvelu=value,
                                                  update_datetime=update_datetime,
                                                  version=1)
        for code in koodisto_codes[key.value]:
            code_obj = Z2_Code.objects.create(koodisto=koodisto_obj, code_value=code)
            for lang in koodistopalvelu.LANGUAGE_CODES:
                Z2_CodeTranslation.objects.create(code=code_obj, language=lang, name='test nimi',
                                                  description='test kuvaus', short_name='test lyhyt nimi')


def get_vakajarjestaja_oids(create_all_vakajarjestajat):
    vakajarjestaja_oids = [
        '1.2.246.562.10.27580498759'        # Parikkalan kunta
    ]

    if create_all_vakajarjestajat:
        vakajarjestaja_oids += [
            '1.2.246.562.10.346830761110',  # Helsingin kaupunki
            '1.2.246.562.10.80381044462',   # Oulun kaupunki
            '1.2.246.562.10.31167956643',   # Tuusulan kunta
            '1.2.246.562.10.94081735717',   # Puumalan kunta
            '1.2.246.562.10.55100459001',   # Rauman kaupunki
            '1.2.246.562.10.73948983488',   # Järvenpään kaupunki
            '1.2.246.562.10.56820737825',   # Turun kaupunki
            '1.2.246.562.10.36026576342',   # Luumäen kunta
            '1.2.246.562.10.90008375488',   # Espoon kaupunki
            '1.2.246.562.10.111870344810',  # Utsjoen kunta
            '1.2.246.562.10.57993240753',   # Pietarsaaren kaupunki
        ]

    return vakajarjestaja_oids


def fetch_huoltajat_if_applicable():
    import os
    from varda.tasks import fetch_huoltajat_task
    if "VARDA_ENVIRONMENT_TYPE" in os.environ:
        fetch_huoltajat_task.delay()


def create_onr_lapsi_huoltajat(create_all_vakajarjestajat=False):
    """
    https://wiki.eduuni.fi/display/CscVarda/Testihuoltajat
    """
    from django.contrib.auth.models import Group, User
    from guardian.shortcuts import assign_perm
    from varda.models import Henkilo, Lapsi
    from varda.organisaatiopalvelu import create_vakajarjestaja_using_oid

    print('Adding lapset + huoltajat (from ONR) in test data.')

    vakajarjestaja_view_henkilo_group = Group.objects.get(name='vakajarjestaja_view_henkilo')
    admin_user = User.objects.get(username='credadmin')

    henkilo_1, henkilo_1_created = Henkilo.objects.get_or_create(
        henkilo_oid='1.2.246.562.24.68159811823',
        defaults={
            'henkilotunnus': 'gAAAAABeOX1kRyEYLW_6z3YCD3vApCjVNJwR4M-ExlfAKqWLvQJZ__6Ztxqha-S0DmuxjZchXlNN2hVIMisYZLDXXzY2fk1IJQ==',
            'henkilotunnus_unique_hash': 'd1206ea57e7fd86f2f7c50fe572936a1b6639128a8ca9941b1c8f66037e0fa83',
            'syntyma_pvm': '2012-01-14',
            'etunimet': 'Jokke',
            'kutsumanimi': 'Jokke',
            'sukunimi': 'Jokunen',
            'aidinkieli_koodi': 'FI',
            'kotikunta_koodi': '091',
            'turvakielto': False,
            'sukupuoli_koodi': 1,
            'katuosoite': '',
            'postinumero': '',
            'postitoimipaikka': '',
            'changed_by': admin_user
        }
    )

    henkilo_2, henkilo_2_created = Henkilo.objects.get_or_create(
        henkilo_oid='1.2.246.562.24.49084901393',
        defaults={
            'henkilotunnus': 'gAAAAABeOX14By1klio088ccJeF6-hSRJ7LZdneYM85hdQQzq1D2N7JS1rYTOQk_gwftL1wkMog4sjXlA_RXDPBNGKT1gUvNDw==',
            'henkilotunnus_unique_hash': 'd9becaf41cd69a312f39a9bb1d0974257423a84b2b6b8d95d7c51922ad6a8bbc',
            'syntyma_pvm': '2012-10-15',
            'etunimet': 'Jaska',
            'kutsumanimi': 'Jaska',
            'sukunimi': 'Joku',
            'aidinkieli_koodi': 'FI',
            'kotikunta_koodi': '091',
            'turvakielto': False,
            'sukupuoli_koodi': 2,
            'katuosoite': '',
            'postinumero': '',
            'postitoimipaikka': '',
            'changed_by': admin_user
        }
    )

    henkilo_3, henkilo_3_created = Henkilo.objects.get_or_create(
        henkilo_oid='1.2.246.562.24.65027773627',
        defaults={
            'henkilotunnus': 'gAAAAABeOX2KpfzGhI-8NHJeD6y5GN-2AW-rBNljGHN-dATt4vnhuwXANY8lS3yk2OKb7Ap_ChaZxpg4wpQ6OR2MuyoI9yzl-w==',
            'henkilotunnus_unique_hash': '05b5dce8a3c078b9861dda10a01290c085473b9764e083935d30ba8baadc09a7',
            'syntyma_pvm': '2015-06-24',
            'etunimet': 'Matti Mikael',
            'kutsumanimi': 'Matti',
            'sukunimi': 'Esimerkki',
            'aidinkieli_koodi': 'FI',
            'kotikunta_koodi': '091',
            'turvakielto': False,
            'sukupuoli_koodi': 1,
            'katuosoite': '',
            'postinumero': '',
            'postitoimipaikka': '',
            'changed_by': admin_user
        }
    )

    henkilo_4, henkilo_4_created = Henkilo.objects.get_or_create(
        henkilo_oid='1.2.246.562.24.86721655046',
        defaults={
            'henkilotunnus': 'gAAAAABeOX2cvW10r98xVX8XEcoYQeeSkQrlduGif7O0goMcaN5WBolz625GBHl_JF64lMsm5RAIWEcs7JO3qfGO0VGMwe5BRw==',
            'henkilotunnus_unique_hash': '1dad3c4e6e1fc076cd11ecb49f39d88a40678425a129394a51d02709b3168f55',
            'syntyma_pvm': '2019-06-04',
            'etunimet': 'Matti',
            'kutsumanimi': 'Matti',
            'sukunimi': 'Tolonen',
            'aidinkieli_koodi': 'FI',
            'kotikunta_koodi': '091',
            'turvakielto': False,
            'sukupuoli_koodi': 1,
            'katuosoite': '',
            'postinumero': '',
            'postitoimipaikka': '',
            'changed_by': admin_user
        }
    )

    vakajarjestaja_oids = get_vakajarjestaja_oids(create_all_vakajarjestajat)
    for organisaatio_oid in vakajarjestaja_oids:
        create_vakajarjestaja_using_oid(organisaatio_oid, 2)

        group_tallentaja = Group.objects.get(name='VARDA-TALLENTAJA_' + organisaatio_oid)
        group_katselija = Group.objects.get(name='VARDA-KATSELIJA_' + organisaatio_oid)
        group_paakayttaja = Group.objects.get(name='VARDA-PAAKAYTTAJA_' + organisaatio_oid)
        group_huoltajatiedot_tallentaja = Group.objects.get(name='HUOLTAJATIETO_TALLENNUS_' + organisaatio_oid)
        group_huoltajatiedot_katselija = Group.objects.get(name='HUOLTAJATIETO_KATSELU_' + organisaatio_oid)

        vakajarjestaja_permission_groups = [group_tallentaja, group_katselija, group_paakayttaja,
                                            group_huoltajatiedot_tallentaja, group_huoltajatiedot_katselija]

        if henkilo_1_created:
            assign_perm('view_henkilo', vakajarjestaja_view_henkilo_group, henkilo_1)
            lapsi_1 = Lapsi.objects.create(
                henkilo=henkilo_1,
                changed_by=admin_user
            )
            for permission_group in vakajarjestaja_permission_groups:
                assign_perm('change_lapsi', permission_group, lapsi_1)

        if henkilo_2_created:
            assign_perm('view_henkilo', vakajarjestaja_view_henkilo_group, henkilo_2)
            lapsi_2 = Lapsi.objects.create(
                henkilo=henkilo_2,
                changed_by=admin_user
            )
            for permission_group in vakajarjestaja_permission_groups:
                assign_perm('view_lapsi', permission_group, lapsi_2)

        if henkilo_3_created:
            assign_perm('view_henkilo', vakajarjestaja_view_henkilo_group, henkilo_3)
            lapsi_3 = Lapsi.objects.create(
                henkilo=henkilo_3,
                changed_by=admin_user
            )
            for permission_group in vakajarjestaja_permission_groups:
                assign_perm('view_lapsi', permission_group, lapsi_3)

        if henkilo_4_created:
            assign_perm('view_henkilo', vakajarjestaja_view_henkilo_group, henkilo_4)
            lapsi_4 = Lapsi.objects.create(
                henkilo=henkilo_4,
                changed_by=admin_user
            )
            for permission_group in vakajarjestaja_permission_groups:
                assign_perm('view_lapsi', permission_group, lapsi_4)

    fetch_huoltajat_if_applicable()


def create_test_data():
    from django.conf import settings
    import os

    create_vakajarjestajat()
    create_toimipaikat_and_painotukset()
    create_henkilot()
    create_lapset()
    create_huoltajat()
    create_huoltajuussuhteet()
    create_user_data()
    create_koodisto_data()
    create_maksutiedot()
    create_paos_toiminta()
    create_paos_oikeus()

    """
    Currently do not populate lapset+huoltajat in db if
    - testing or
    - missing env variables: OPINTOPOLKU_USERNAME / OPINTOPOLKU_PASSWORD
    """
    opintopolku_username = os.getenv('OPINTOPOLKU_USERNAME', None)
    opintopolku_password = os.getenv('OPINTOPOLKU_PASSWORD', None)
    if settings.TESTING or opintopolku_username is None or opintopolku_password is None:
        pass
    else:
        create_onr_lapsi_huoltajat()


def load_testing_data():
    add_groups_with_permissions()
    add_test_users()
    create_test_data()
