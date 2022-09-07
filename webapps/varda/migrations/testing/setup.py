import json
import logging

from varda.enums.tietosisalto_ryhma import TietosisaltoRyhma


logger = logging.getLogger(__name__)


def add_test_users():
    from django.contrib.auth.models import User

    User.objects.create(username='tester', password='pbkdf2_sha256$120000$4IdDHxUJJSE6$N18zHZK02yA3KxNeTcDS4t6Ytsn2ZOLO6QLDXNT/8Yo=')
    User.objects.create(username='tester2', password='pbkdf2_sha256$120000$gNFFj5K8ZgTu$quUQQlMXZCs+1mG+nbBpTS/VXRZAy47XkR7EoioNLkQ=')
    User.objects.create(username='tester3', password='pbkdf2_sha256$150000$kfJSJbENiF5k$tZ3aa9ErAy1Ciszx40KdRMU787p7HnKHjVOQ+lzDF7U=')
    User.objects.create(username='tester4', password='pbkdf2_sha256$150000$LFrFAT6FakMM$VuLb0n11tVR0tlIBAmykLWP4an5zv4XWseGHJDlnsWk=')
    User.objects.create(username='tester5', password='pbkdf2_sha256$150000$ZX2pJZZ34sR6$XUs0RUe6IZYNdn7vYxIvm+05Ruw4brTbYG70Q3oH31s=')
    User.objects.create(username='varda-testi', password='pbkdf2_sha256$120000$0wwPCIArT7tR$OVGZGiJoJe7wqcP1CG4orfA31MUrMXlI5fHcnOUzcIw=')
    User.objects.create(username='tester-e2e', password='pbkdf2_sha256$120000$6ihvwx47epob$a2xDB6OLThL4eeEuMVw8+3QB1QBxi5hU2gZxnMwA2nE=')
    User.objects.create(username='pkvakajarjestaja1', password='pbkdf2_sha256$150000$rBZO8vnXaxun$MhKN0NOCnasVgrMsIkYfIBXaBDdRiRy8J7WQM62bARY=')
    User.objects.create(username='pkvakajarjestaja2', password='pbkdf2_sha256$150000$ptRhdza1ttgB$IJdKerCPdzhC/wDME/rUVzFTKflh2coUuaCGWomg+Lo=')
    User.objects.create(username='huoltajatietojen_tallentaja', password='pbkdf2_sha256$150000$S3mQ66CWYdSO$o9T08pdVyIZFqbdC8pK5cMk2O64d3xfQdw2x2vzr4M8=')
    User.objects.create(username='vakatietojen_tallentaja', password='pbkdf2_sha256$150000$S3mQ66CWYdSO$o9T08pdVyIZFqbdC8pK5cMk2O64d3xfQdw2x2vzr4M8=')
    User.objects.create(username='vakatietojen_toimipaikka_tallentaja', password='pbkdf2_sha256$150000$S3mQ66CWYdSO$o9T08pdVyIZFqbdC8pK5cMk2O64d3xfQdw2x2vzr4M8=')
    User.objects.create(username='vakatietojen_toimipaikka_tallentaja_9395737548815', password='pbkdf2_sha256$150000$ntAfCrXVuXnI$A63mBzAb7EzHDdR6jTSGZDmmYj0OtfbgetIFbtBZXBo=')
    User.objects.create(username='tester7', password='pbkdf2_sha256$150000$9fuSiDHlpxu4$qpRt5+aPs8Fd9VsI0XPjOvMHCN7LF+VbSJLyIghrNks=')
    User.objects.create(username='tester8', password='pbkdf2_sha256$150000$e5HLX1BadPnp$4H0r3yNEbiaTZ2yJ07HFK+8GsUM5JwKGNa/O727IOtI=')
    User.objects.create(username='tester9', password='pbkdf2_sha256$150000$ntAfCrXVuXnI$A63mBzAb7EzHDdR6jTSGZDmmYj0OtfbgetIFbtBZXBo=')
    User.objects.create(username='tyontekija_tallentaja', password='pbkdf2_sha256$150000$ntAfCrXVuXnI$A63mBzAb7EzHDdR6jTSGZDmmYj0OtfbgetIFbtBZXBo=')
    User.objects.create(username='tyontekija_katselija', password='pbkdf2_sha256$150000$ntAfCrXVuXnI$A63mBzAb7EzHDdR6jTSGZDmmYj0OtfbgetIFbtBZXBo=')
    User.objects.create(username='tyontekija_toimipaikka_tallentaja', password='pbkdf2_sha256$150000$ntAfCrXVuXnI$A63mBzAb7EzHDdR6jTSGZDmmYj0OtfbgetIFbtBZXBo=')
    User.objects.create(username='tyontekija_toimipaikka_tallentaja_9395737548815', password='pbkdf2_sha256$150000$ntAfCrXVuXnI$A63mBzAb7EzHDdR6jTSGZDmmYj0OtfbgetIFbtBZXBo=')
    User.objects.create(username='tyontekija_toimipaikka_katselija', password='pbkdf2_sha256$150000$ntAfCrXVuXnI$A63mBzAb7EzHDdR6jTSGZDmmYj0OtfbgetIFbtBZXBo=')
    User.objects.create(username='tilapaiset_tallentaja', password='pbkdf2_sha256$150000$ntAfCrXVuXnI$A63mBzAb7EzHDdR6jTSGZDmmYj0OtfbgetIFbtBZXBo=')
    User.objects.create(username='taydennyskoulutus_tallentaja', password='pbkdf2_sha256$150000$ntAfCrXVuXnI$A63mBzAb7EzHDdR6jTSGZDmmYj0OtfbgetIFbtBZXBo=')
    User.objects.create(username='taydennyskoulutus_toimipaikka_tallentaja', password='pbkdf2_sha256$150000$ntAfCrXVuXnI$A63mBzAb7EzHDdR6jTSGZDmmYj0OtfbgetIFbtBZXBo=')
    User.objects.create(username='taydennyskoulutus_toimipaikka_katselija', password='pbkdf2_sha256$150000$ntAfCrXVuXnI$A63mBzAb7EzHDdR6jTSGZDmmYj0OtfbgetIFbtBZXBo=')
    User.objects.create(username='tester10', password='pbkdf2_sha256$150000$OULQV9qeoPsD$dH1fxZUMGFNjSM3xQzknGRJjndCUMNTj3+nyK+ET0Gc=')
    User.objects.create(username='tester11', password='pbkdf2_sha256$150000$9HnlY5WRksmT$J5TselErYqb9w2upEbgzsFwJ8tvfbU5U8y7Zj5QQJPk=')
    User.objects.create(username='tester-no-known-privileges', password='pbkdf2_sha256$120000$6ihvwx47epob$a2xDB6OLThL4eeEuMVw8+3QB1QBxi5hU2gZxnMwA2nE=')
    User.objects.create(username='henkilosto_tallentaja_93957375488', password='pbkdf2_sha256$150000$WMst0ZmwKf3p$Fqyz4SSdybbBdAexKCjxXyqiUfYafn7XxGaxQsALqoo=')
    User.objects.create(username='kela_luovutuspalvelu', password='pbkdf2_sha256$150000$WMst0ZmwKQ5P$Fqyz1KLMdybbBdjLmKCjxXyqiUfYafn7XxGaxQsALqoo=')
    User.objects.create(username='varda_system', password='pbkdf2_sha256$150000$WMst9QvKQ5P$Fqyz1HDLdybbBdjiKlCjxXyqiUfYafn7XxGaxQsALqoo=')
    User.objects.create(username='user_toimipaikka_9395737548810', password='pbkdf2_sha256$150000$WMst0ZmwKf3p$Fqyz4SSdybbBdAexKCjxXyqiUfYafn7XxGaxQsALqoo=')


def add_test_user_permissions():
    from django.contrib.auth.models import Group, User

    group_palvelukayttaja = Group.objects.get(name='vakajarjestaja_palvelukayttaja')
    group_palvelukayttaja_vakajarjestaja_1 = Group.objects.get(name='VARDA-PALVELUKAYTTAJA_1.2.246.562.10.34683023489')
    group_palvelukayttaja_vakajarjestaja_2 = Group.objects.get(name='VARDA-PALVELUKAYTTAJA_1.2.246.562.10.93957375488')
    group_tallentaja_vakajarjestaja_2 = Group.objects.get(name='VARDA-TALLENTAJA_1.2.246.562.10.93957375488')
    group_tallentaja_toimipaikka_1 = Group.objects.get(name='VARDA-TALLENTAJA_1.2.246.562.10.9395737548810')
    group_tallentaja_toimipaikka_2 = Group.objects.get(name='VARDA-TALLENTAJA_1.2.246.562.10.9395737548815')
    group_katselija_toimipaikka_4 = Group.objects.get(name='VARDA-KATSELIJA_1.2.246.562.10.9395737548811')
    group_tallentaja_vakajarjestaja_1 = Group.objects.get(name='VARDA-TALLENTAJA_1.2.246.562.10.34683023489')
    group_tallentaja_toimipaikka_5 = Group.objects.get(name='VARDA-TALLENTAJA_1.2.246.562.10.9395737548817')
    group_tallentaja_toimipaikka_9395737548815 = Group.objects.get(name='VARDA-TALLENTAJA_1.2.246.562.10.9395737548815')
    group_paakayttaja_vakajarjestaja_1 = Group.objects.get(name='VARDA-PAAKAYTTAJA_1.2.246.562.10.34683023489')
    group_paakayttaja_vakajarjestaja_2 = Group.objects.get(name='VARDA-PAAKAYTTAJA_1.2.246.562.10.93957375488')
    group_huoltajatiedot_tallentaja_toimipaikka_1 = Group.objects.get(name='HUOLTAJATIETO_TALLENNUS_1.2.246.562.10.9395737548810')
    group_huoltajatiedot_tallentaja_vakajarjestaja_1 = Group.objects.get(name='HUOLTAJATIETO_TALLENNUS_1.2.246.562.10.34683023489')
    group_huoltajatiedot_tallentaja_vakajarjestaja_2 = Group.objects.get(name='HUOLTAJATIETO_TALLENNUS_1.2.246.562.10.93957375488')
    group_huoltajatiedot_tallentaja_toimipaikka_5 = Group.objects.get(name='HUOLTAJATIETO_TALLENNUS_1.2.246.562.10.9395737548817')
    group_huoltajatiedot_tallentaja_toimipaikka_2935996863483 = Group.objects.get(name='HUOLTAJATIETO_TALLENNUS_1.2.246.562.10.2935996863483')
    group_tallentaja_toimipaikka_2935996863483 = Group.objects.get(name='VARDA-TALLENTAJA_1.2.246.562.10.2935996863483')
    group_tyontekija_tallentaja_vakajarjestaja1 = Group.objects.get(name='HENKILOSTO_TYONTEKIJA_TALLENTAJA_1.2.246.562.10.34683023489')
    group_tyontekija_tallentaja_vakajarjestaja2 = Group.objects.get(name='HENKILOSTO_TYONTEKIJA_TALLENTAJA_1.2.246.562.10.93957375488')
    group_tyontekija_katselija_vakajarjestaja1 = Group.objects.get(name='HENKILOSTO_TYONTEKIJA_KATSELIJA_1.2.246.562.10.34683023489')
    group_tyontekija_tallentaja_toimipaikka1 = Group.objects.get(name='HENKILOSTO_TYONTEKIJA_TALLENTAJA_1.2.246.562.10.9395737548810')
    group_tyontekija_tallentaja_toimipaikka_9395737548815 = Group.objects.get(name='HENKILOSTO_TYONTEKIJA_TALLENTAJA_1.2.246.562.10.9395737548815')
    group_tyontekija_katselija_toimipaikka1 = Group.objects.get(name='HENKILOSTO_TYONTEKIJA_KATSELIJA_1.2.246.562.10.9395737548810')
    group_tilapaiset_tallentaja_vakajarjestaja1 = Group.objects.get(name='HENKILOSTO_TILAPAISET_TALLENTAJA_1.2.246.562.10.34683023489')
    group_taydennys_tallentaja_vakajarjestaja1 = Group.objects.get(name='HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA_1.2.246.562.10.34683023489')
    group_taydennys_tallentaja_vakajarjestaja2 = Group.objects.get(name='HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA_1.2.246.562.10.93957375488')
    group_taydennys_tallentaja_toimipaikka1 = Group.objects.get(name='HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA_1.2.246.562.10.9395737548810')
    group_taydennys_katselija_toimipaikka1 = Group.objects.get(name='HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA_1.2.246.562.10.9395737548810')
    group_paakayttaja_vakajarjestaja_57294396385 = Group.objects.get(name='VARDA-PAAKAYTTAJA_1.2.246.562.10.57294396385')
    group_tallentaja_vakajarjestaja_57294396385 = Group.objects.get(name='VARDA-TALLENTAJA_1.2.246.562.10.57294396385')
    group_huoltajatiedot_tallentaja_vakajarjestaja_57294396385 = Group.objects.get(name='HUOLTAJATIETO_TALLENNUS_1.2.246.562.10.57294396385')
    group_tyontekija_tallentaja_vakajarjestaja_57294396385 = Group.objects.get(name='HENKILOSTO_TYONTEKIJA_TALLENTAJA_1.2.246.562.10.57294396385')
    group_tilapaiset_tallentaja_vakajarjestaja_57294396385 = Group.objects.get(name='HENKILOSTO_TILAPAISET_TALLENTAJA_1.2.246.562.10.57294396385')
    group_taydennys_tallentaja_vakajarjestaja_57294396385 = Group.objects.get(name='HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA_1.2.246.562.10.57294396385')
    group_paakayttaja_vakajarjestaja_52966755795 = Group.objects.get(name='VARDA-PAAKAYTTAJA_1.2.246.562.10.52966755795')
    group_tallentaja_vakajarjestaja_52966755795 = Group.objects.get(name='VARDA-TALLENTAJA_1.2.246.562.10.52966755795')
    group_huoltajatiedot_tallentaja_vakajarjestaja_52966755795 = Group.objects.get(name='HUOLTAJATIETO_TALLENNUS_1.2.246.562.10.52966755795')
    group_tyontekija_tallentaja_vakajarjestaja_52966755795 = Group.objects.get(name='HENKILOSTO_TYONTEKIJA_TALLENTAJA_1.2.246.562.10.52966755795')
    group_tilapaiset_tallentaja_vakajarjestaja_52966755795 = Group.objects.get(name='HENKILOSTO_TILAPAISET_TALLENTAJA_1.2.246.562.10.52966755795')
    group_taydennys_tallentaja_vakajarjestaja_52966755795 = Group.objects.get(name='HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA_1.2.246.562.10.52966755795')
    group_toimijatiedot_tallentaja_34683023489 = Group.objects.get(name='VARDA_TOIMIJATIEDOT_TALLENTAJA_1.2.246.562.10.34683023489')
    group_toimijatiedot_tallentaja_57294396385 = Group.objects.get(name='VARDA_TOIMIJATIEDOT_TALLENTAJA_1.2.246.562.10.57294396385')
    group_toimijatiedot_tallentaja_52966755795 = Group.objects.get(name='VARDA_TOIMIJATIEDOT_TALLENTAJA_1.2.246.562.10.52966755795')
    group_raporttien_katselija_34683023489 = Group.objects.get(name='VARDA_RAPORTTIEN_KATSELIJA_1.2.246.562.10.34683023489')
    group_kela_luovutuspalvelu = Group.objects.get(name='VARDA_LUOVUTUSPALVELU_1.2.246.562.10.2013121014482686198719')

    user_tester = User.objects.get(username='tester')
    user_tester.groups.add(group_tallentaja_toimipaikka_1)
    user_tester.groups.add(group_katselija_toimipaikka_4)
    user_tester.groups.add(group_huoltajatiedot_tallentaja_toimipaikka_1)
    user_tester.groups.add(group_tallentaja_toimipaikka_2935996863483)
    user_tester.groups.add(group_huoltajatiedot_tallentaja_toimipaikka_2935996863483)
    user_tester.groups.add(group_huoltajatiedot_tallentaja_vakajarjestaja_1)

    user_tester2 = User.objects.get(username='tester2')
    user_tester2.groups.add(group_tallentaja_vakajarjestaja_1)
    user_tester2.groups.add(group_huoltajatiedot_tallentaja_vakajarjestaja_1)
    user_tester2.groups.add(group_toimijatiedot_tallentaja_34683023489)
    user_tester2.groups.add(group_raporttien_katselija_34683023489)

    user_tester3 = User.objects.get(username='tester3')
    user_tester3.groups.add(group_paakayttaja_vakajarjestaja_2)

    user_tester4 = User.objects.get(username='tester4')
    user_tester4.groups.add(group_paakayttaja_vakajarjestaja_1)

    user_tester5 = User.objects.get(username='tester5')
    user_tester5.groups.add(group_tallentaja_vakajarjestaja_2)

    user_varda_testi = User.objects.get(username='varda-testi')
    user_varda_testi.groups.add(group_palvelukayttaja)

    user_tester_e2e = User.objects.get(username='tester-e2e')
    user_tester_e2e.groups.add(group_palvelukayttaja)

    user_palvelukayttaja_vakajarjestaja_1 = User.objects.get(username='pkvakajarjestaja1')
    user_palvelukayttaja_vakajarjestaja_1.groups.add(group_palvelukayttaja_vakajarjestaja_1)

    user_palvelukayttaja_vakajarjestaja_2 = User.objects.get(username='pkvakajarjestaja2')
    user_palvelukayttaja_vakajarjestaja_2.groups.add(group_palvelukayttaja_vakajarjestaja_2)

    huoltajatietojen_tallentaja = User.objects.get(username='huoltajatietojen_tallentaja')
    huoltajatietojen_tallentaja.groups.add(group_huoltajatiedot_tallentaja_vakajarjestaja_1)

    vakatietojen_tallentaja = User.objects.get(username='vakatietojen_tallentaja')
    vakatietojen_tallentaja.groups.add(group_tallentaja_vakajarjestaja_1)

    vakatietojen_toimipaikka_tallentaja = User.objects.get(username='vakatietojen_toimipaikka_tallentaja')
    vakatietojen_toimipaikka_tallentaja.groups.add(group_tallentaja_toimipaikka_1)
    vakatietojen_toimipaikka_tallentaja.groups.add(group_tallentaja_toimipaikka_2)

    vakatietojen_toimipaikka_tallentaja_9395737548815 = User.objects.get(username='vakatietojen_toimipaikka_tallentaja_9395737548815')
    vakatietojen_toimipaikka_tallentaja_9395737548815.groups.add(group_tallentaja_toimipaikka_9395737548815)

    user_toimipaikka_9395737548810 = User.objects.get(username='user_toimipaikka_9395737548810')
    user_toimipaikka_9395737548810.groups.add(group_tallentaja_toimipaikka_1)
    user_toimipaikka_9395737548810.groups.add(group_huoltajatiedot_tallentaja_toimipaikka_1)

    user_tester7 = User.objects.get(username='tester7')
    user_tester7.groups.add(group_huoltajatiedot_tallentaja_vakajarjestaja_2)

    user_tester8 = User.objects.get(username='tester8')
    user_tester8.groups.add(group_tallentaja_toimipaikka_5)

    user_tester9 = User.objects.get(username='tester9')
    user_tester9.groups.add(group_huoltajatiedot_tallentaja_toimipaikka_5)

    tyontekija_tallentaja = User.objects.get(username='tyontekija_tallentaja')
    tyontekija_tallentaja.groups.add(group_tyontekija_tallentaja_vakajarjestaja1)

    tyontekija_katselija = User.objects.get(username='tyontekija_katselija')
    tyontekija_katselija.groups.add(group_tyontekija_katselija_vakajarjestaja1)

    tyontekija_toimipaikka_tallentaja = User.objects.get(username='tyontekija_toimipaikka_tallentaja')
    tyontekija_toimipaikka_tallentaja.groups.add(group_tyontekija_tallentaja_toimipaikka1)

    tyontekija_toimipaikka_tallentaja_9395737548815 = User.objects.get(username='tyontekija_toimipaikka_tallentaja_9395737548815')
    tyontekija_toimipaikka_tallentaja_9395737548815.groups.add(group_tyontekija_tallentaja_toimipaikka_9395737548815)

    tyontekija_toimipaikka_katselija = User.objects.get(username='tyontekija_toimipaikka_katselija')
    tyontekija_toimipaikka_katselija.groups.add(group_tyontekija_katselija_toimipaikka1)

    tilapaiset_tallentaja = User.objects.get(username='tilapaiset_tallentaja')
    tilapaiset_tallentaja.groups.add(group_tilapaiset_tallentaja_vakajarjestaja1)

    taydennyskoulutus_tallentaja = User.objects.get(username='taydennyskoulutus_tallentaja')
    taydennyskoulutus_tallentaja.groups.add(group_taydennys_tallentaja_vakajarjestaja1)

    taydennyskoulutus_toimipaikka_tallentaja = User.objects.get(username='taydennyskoulutus_toimipaikka_tallentaja')
    taydennyskoulutus_toimipaikka_tallentaja.groups.add(group_taydennys_tallentaja_toimipaikka1)

    taydennyskoulutus_toimipaikka_katselija = User.objects.get(username='taydennyskoulutus_toimipaikka_katselija')
    taydennyskoulutus_toimipaikka_katselija.groups.add(group_taydennys_katselija_toimipaikka1)

    user_tester10 = User.objects.get(username='tester10')
    user_tester10.groups.add(group_paakayttaja_vakajarjestaja_57294396385)
    user_tester10.groups.add(group_tallentaja_vakajarjestaja_57294396385)
    user_tester10.groups.add(group_huoltajatiedot_tallentaja_vakajarjestaja_57294396385)
    user_tester10.groups.add(group_tyontekija_tallentaja_vakajarjestaja_57294396385)
    user_tester10.groups.add(group_tilapaiset_tallentaja_vakajarjestaja_57294396385)
    user_tester10.groups.add(group_taydennys_tallentaja_vakajarjestaja_57294396385)
    user_tester10.groups.add(group_toimijatiedot_tallentaja_57294396385)

    user_tester11 = User.objects.get(username='tester11')
    user_tester11.groups.add(group_paakayttaja_vakajarjestaja_52966755795)
    user_tester11.groups.add(group_tallentaja_vakajarjestaja_52966755795)
    user_tester11.groups.add(group_huoltajatiedot_tallentaja_vakajarjestaja_52966755795)
    user_tester11.groups.add(group_tyontekija_tallentaja_vakajarjestaja_52966755795)
    user_tester11.groups.add(group_tilapaiset_tallentaja_vakajarjestaja_52966755795)
    user_tester11.groups.add(group_taydennys_tallentaja_vakajarjestaja_52966755795)
    user_tester11.groups.add(group_toimijatiedot_tallentaja_52966755795)

    henkilosto_tallentaja_93957375488 = User.objects.get(username='henkilosto_tallentaja_93957375488')
    henkilosto_tallentaja_93957375488.groups.add(group_tyontekija_tallentaja_vakajarjestaja2)
    henkilosto_tallentaja_93957375488.groups.add(group_taydennys_tallentaja_vakajarjestaja2)

    kela_luovutuspalvelu = User.objects.get(username='kela_luovutuspalvelu')
    kela_luovutuspalvelu.groups.add(group_kela_luovutuspalvelu)


def create_vakajarjestajat():
    from django.conf import settings
    from varda.enums.organisaatiotyyppi import Organisaatiotyyppi
    from varda.models import Organisaatio
    from varda.permissions import assign_organisaatio_permissions
    from varda.permission_groups import create_permission_groups_for_organisaatio

    organisaatio_list = (
        Organisaatio.objects.create(
            nimi='Tester2 organisaatio',
            y_tunnus='8500570-7',
            organisaatio_oid='1.2.246.562.10.34683023489',
            kunta_koodi='091',
            sahkopostiosoite='organization@domain.com',
            kayntiosoite='Testerkatu 2',
            kayntiosoite_postinumero='00001',
            kayntiosoite_postitoimipaikka='Testilä',
            postiosoite='Testerkatu 2',
            postitoimipaikka='Testilä',
            postinumero='00001',
            puhelinnumero='+358101234567',
            yritysmuoto='41',
            alkamis_pvm='2017-02-03',
            paattymis_pvm=None,
            integraatio_organisaatio=[TietosisaltoRyhma.VAKATIEDOT.value],
            organisaatiotyyppi=[Organisaatiotyyppi.VAKAJARJESTAJA.value]
        ),
        Organisaatio.objects.create(
            nimi='Tester organisaatio',
            y_tunnus='1825748-8',
            organisaatio_oid='1.2.246.562.10.93957375488',
            kunta_koodi='049',
            sahkopostiosoite='organization@domain.com',
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
            yritysmuoto='16',
            integraatio_organisaatio=[],
            organisaatiotyyppi=[Organisaatiotyyppi.VAKAJARJESTAJA.value]
        ),
        Organisaatio.objects.create(
            nimi='varda-testi organisaatio',
            y_tunnus='2617455-1',
            organisaatio_oid='1.2.246.562.10.93957375486',
            kunta_koodi='',
            sahkopostiosoite='varda-testi@email.fi',
            kayntiosoite='Testilä 3',
            kayntiosoite_postinumero='10001',
            kayntiosoite_postitoimipaikka='Testilä',
            postiosoite='Testilä3',
            postitoimipaikka='Testilä',
            postinumero='10001',
            puhelinnumero='+358451234567',
            alkamis_pvm='2018-09-13',
            paattymis_pvm=None,
            integraatio_organisaatio=[],
            organisaatiotyyppi=[Organisaatiotyyppi.VAKAJARJESTAJA.value]
        ),
        Organisaatio.objects.create(
            nimi='Frontti organisaatio',
            y_tunnus='2156233-6',
            organisaatio_oid='1.2.246.562.10.93957375484',
            kunta_koodi='230',
            sahkopostiosoite='frontti@end.com',
            kayntiosoite='Fronttikuja 12',
            kayntiosoite_postinumero='54321',
            kayntiosoite_postitoimipaikka='Fronttila',
            postiosoite='Fronttikuja 12',
            postitoimipaikka='Fronttila',
            postinumero='54321',
            puhelinnumero='+358505432109',
            yritysmuoto='42',
            alkamis_pvm='2018-09-25',
            paattymis_pvm=None,
            integraatio_organisaatio=[],
            organisaatiotyyppi=[Organisaatiotyyppi.VAKAJARJESTAJA.value]
        ),
        Organisaatio.objects.create(
            nimi='Tester 10 organisaatio',
            y_tunnus='8685083-0',
            organisaatio_oid='1.2.246.562.10.57294396385',
            kunta_koodi='405',
            sahkopostiosoite='tester10@domain.com',
            kayntiosoite='Kottaraisenkuja 12',
            kayntiosoite_postinumero='12345',
            kayntiosoite_postitoimipaikka='Testilä',
            postiosoite='Kottaraisenkuja 12',
            postitoimipaikka='Testilä',
            postinumero='12345',
            puhelinnumero='+358501231234',
            yritysmuoto='42',
            alkamis_pvm='2019-01-01',
            paattymis_pvm=None,
            integraatio_organisaatio=[],
            organisaatiotyyppi=[Organisaatiotyyppi.VAKAJARJESTAJA.value]
        ),
        Organisaatio.objects.create(
            nimi='Tester 11 organisaatio',
            y_tunnus='1428881-8',
            organisaatio_oid='1.2.246.562.10.52966755795',
            kunta_koodi='297',
            sahkopostiosoite='tester11@domain.com',
            kayntiosoite='Brianinkuja 1',
            kayntiosoite_postinumero='12345',
            kayntiosoite_postitoimipaikka='Testilä',
            postiosoite='Brianinkuja 1',
            postitoimipaikka='Testilä',
            postinumero='12345',
            puhelinnumero='+358401231234',
            yritysmuoto='42',
            alkamis_pvm='2019-02-01',
            paattymis_pvm=None,
            integraatio_organisaatio=[],
            organisaatiotyyppi=[Organisaatiotyyppi.VAKAJARJESTAJA.value]
        ),
        Organisaatio.objects.create(
            nimi='Kansaneläkelaitos',
            y_tunnus='0246246-0',
            organisaatio_oid='1.2.246.562.10.2013121014482686198719',
            kunta_koodi='091',
            sahkopostiosoite='',
            kayntiosoite='',
            kayntiosoite_postinumero='',
            kayntiosoite_postitoimipaikka='',
            postiosoite='',
            postitoimipaikka='',
            postinumero='',
            puhelinnumero='',
            yritysmuoto='48',
            alkamis_pvm='1979-01-02',
            paattymis_pvm=None,
            integraatio_organisaatio=[],
            organisaatiotyyppi=[Organisaatiotyyppi.MUU.value]
        ),
        Organisaatio.objects.create(
            nimi='Opetushallitus',
            y_tunnus='',
            organisaatio_oid=settings.OPETUSHALLITUS_ORGANISAATIO_OID,
            kunta_koodi='',
            sahkopostiosoite='',
            kayntiosoite='',
            kayntiosoite_postinumero='',
            kayntiosoite_postitoimipaikka='',
            postiosoite='',
            postitoimipaikka='',
            postinumero='',
            puhelinnumero='',
            yritysmuoto='0',
            alkamis_pvm='1970-01-01',
            paattymis_pvm=None,
            integraatio_organisaatio=[],
            organisaatiotyyppi=[Organisaatiotyyppi.MUU.value]
        )
    )

    for organisaatio in organisaatio_list:
        organisaatio_oid = organisaatio.organisaatio_oid
        create_permission_groups_for_organisaatio(organisaatio_oid, organisaatio.organisaatiotyyppi[0])
        assign_organisaatio_permissions(organisaatio)


def create_toimipaikat_and_painotukset():
    from varda.enums.organisaatiotyyppi import Organisaatiotyyppi
    from varda.models import Toimipaikka, Organisaatio
    from varda.permissions import assign_toimipaikka_permissions
    from varda.permission_groups import create_permission_groups_for_organisaatio

    vakajarjestaja_tester_obj = Organisaatio.objects.filter(nimi='Tester organisaatio')[0]
    vakajarjestaja_tester2_obj = Organisaatio.objects.filter(nimi='Tester2 organisaatio')[0]
    vakajarjestaja_4_obj = Organisaatio.objects.get(id=4)
    vakajarjestaja_57294396385 = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.57294396385')
    vakajarjestaja_52966755795 = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.52966755795')

    toimipaikka_list = (
        Toimipaikka.objects.create(
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
            jarjestamismuoto_koodi=['jm02', 'jm03', 'jm04', 'jm05'],
            varhaiskasvatuspaikat=120,
            toiminnallinenpainotus_kytkin=True,
            kielipainotus_kytkin=True,
            alkamis_pvm='2017-02-03',
            paattymis_pvm=None,
            hallinnointijarjestelma='ORGANISAATIO',
            lahdejarjestelma='1',
            tunniste='testing-toimipaikka1'
        ),
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
            jarjestamismuoto_koodi=['jm01', 'jm02', 'jm03'],
            varhaiskasvatuspaikat=200,
            toiminnallinenpainotus_kytkin=False,
            kielipainotus_kytkin=False,
            alkamis_pvm='2017-08-02',
            paattymis_pvm=None,
            lahdejarjestelma='1',
            tunniste='testing-toimipaikka2'
        ),
        Toimipaikka.objects.create(
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
            lahdejarjestelma='1',
            tunniste='testing-toimipaikka3'
        ),
        Toimipaikka.objects.create(
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
            jarjestamismuoto_koodi=['jm03', 'jm04'],
            varhaiskasvatuspaikat=150,
            toiminnallinenpainotus_kytkin=True,
            kielipainotus_kytkin=True,
            alkamis_pvm='2017-01-03',
            paattymis_pvm=None,
            lahdejarjestelma='1',
            tunniste='testing-toimipaikka4'
        ),
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
            jarjestamismuoto_koodi=['jm02', 'jm03', 'jm04', 'jm05'],
            varhaiskasvatuspaikat=150,
            toiminnallinenpainotus_kytkin=True,
            kielipainotus_kytkin=True,
            alkamis_pvm='2017-01-03',
            paattymis_pvm=None,
            lahdejarjestelma='1',
            tunniste='testing-toimipaikka5'
        ),
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
            jarjestamismuoto_koodi=['jm01', 'jm02', 'jm03'],
            varhaiskasvatuspaikat=150,
            toiminnallinenpainotus_kytkin=True,
            kielipainotus_kytkin=True,
            alkamis_pvm='2017-01-03',
            paattymis_pvm=None,
            lahdejarjestelma='1',
            tunniste='testing-toimipaikka6'
        ),
        Toimipaikka.objects.create(
            vakajarjestaja=vakajarjestaja_tester_obj,
            nimi='Espoo yksityinen',
            nimi_sv='Esbo privat',
            organisaatio_oid='1.2.246.562.10.2935996863483',
            kayntiosoite='Makkarakatu 14',
            kayntiosoite_postitoimipaikka='Espoo',
            kayntiosoite_postinumero='02100',
            postiosoite='Keilaranta 14',
            postitoimipaikka='Espoo',
            postinumero='02100',
            kunta_koodi='091',
            puhelinnumero='+35810123456',
            sahkopostiosoite='test5@espoo.fi',
            kasvatusopillinen_jarjestelma_koodi='kj02',
            toimintamuoto_koodi='tm01',
            asiointikieli_koodi=['FI', 'SV'],
            jarjestamismuoto_koodi=['jm05'],
            varhaiskasvatuspaikat=120,
            toiminnallinenpainotus_kytkin=False,
            kielipainotus_kytkin=False,
            alkamis_pvm='2020-02-20',
            paattymis_pvm=None,
            lahdejarjestelma='1',
            tunniste='testing-toimipaikka7'
        ),
        Toimipaikka.objects.create(
            vakajarjestaja=vakajarjestaja_57294396385,
            nimi='tester10 toimipaikka 1',
            nimi_sv='tester10 toimipaikka 1 sv',
            organisaatio_oid='1.2.246.562.10.6727877596658',
            kayntiosoite='Testisentie 6',
            kayntiosoite_postitoimipaikka='Testilä',
            kayntiosoite_postinumero='12345',
            postiosoite='Testisentie 6',
            postitoimipaikka='Testilä',
            postinumero='12345',
            kunta_koodi='405',
            puhelinnumero='+358501234567',
            sahkopostiosoite='test6@domain.com',
            kasvatusopillinen_jarjestelma_koodi='kj03',
            toimintamuoto_koodi='tm01',
            asiointikieli_koodi=['FI', 'SV'],
            jarjestamismuoto_koodi=['jm01'],
            varhaiskasvatuspaikat=100,
            toiminnallinenpainotus_kytkin=False,
            kielipainotus_kytkin=False,
            alkamis_pvm='2018-05-01',
            paattymis_pvm=None,
            lahdejarjestelma='1',
            tunniste='testing-toimipaikka8'
        ),
        Toimipaikka.objects.create(
            vakajarjestaja=vakajarjestaja_57294396385,
            nimi='tester10 toimipaikka 2',
            nimi_sv='tester10 toimipaikka 2 sv',
            organisaatio_oid='1.2.246.562.10.2565458382544',
            kayntiosoite='Testisentie 7',
            kayntiosoite_postitoimipaikka='Testilä',
            kayntiosoite_postinumero='12345',
            postiosoite='Testisentie 7',
            postitoimipaikka='Testilä',
            postinumero='12345',
            kunta_koodi='405',
            puhelinnumero='+358502345678',
            sahkopostiosoite='test6@domain.com',
            kasvatusopillinen_jarjestelma_koodi='kj03',
            toimintamuoto_koodi='tm01',
            asiointikieli_koodi=['FI', 'SV'],
            jarjestamismuoto_koodi=['jm01'],
            varhaiskasvatuspaikat=150,
            toiminnallinenpainotus_kytkin=False,
            kielipainotus_kytkin=False,
            alkamis_pvm='2018-09-01',
            paattymis_pvm=None,
            lahdejarjestelma='1',
            tunniste='testing-toimipaikka9'
        ),
        Toimipaikka.objects.create(
            vakajarjestaja=vakajarjestaja_52966755795,
            nimi='tester11 toimipaikka 1',
            nimi_sv='tester11 toimipaikka 1 sv',
            organisaatio_oid='1.2.246.562.10.9625978384762',
            kayntiosoite='Kottaraisentie 1',
            kayntiosoite_postitoimipaikka='Testilä',
            kayntiosoite_postinumero='12345',
            postiosoite='Kottaraisentie 1',
            postitoimipaikka='Testilä',
            postinumero='12345',
            kunta_koodi='297',
            puhelinnumero='+358501230987',
            sahkopostiosoite='test7@domain.com',
            kasvatusopillinen_jarjestelma_koodi='kj03',
            toimintamuoto_koodi='tm01',
            asiointikieli_koodi=['FI', 'SV'],
            jarjestamismuoto_koodi=['jm01'],
            varhaiskasvatuspaikat=175,
            toiminnallinenpainotus_kytkin=False,
            kielipainotus_kytkin=False,
            alkamis_pvm='2019-03-01',
            paattymis_pvm=None,
            lahdejarjestelma='1',
            tunniste='testing-toimipaikka10'
        )
    )

    for toimipaikka in toimipaikka_list:
        organisaatio_oid = toimipaikka.organisaatio_oid
        create_permission_groups_for_organisaatio(organisaatio_oid, Organisaatiotyyppi.TOIMIPAIKKA.value)
        assign_toimipaikka_permissions(toimipaikka)

    toiminnallinen_painotus_list = (
        {
            'toimipaikka_oid': '1.2.246.562.10.9395737548810',
            'toimintapainotus_koodi': 'tp01',
            'alkamis_pvm': '2017-02-10',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-toiminnallinenpainotus1'
        },
        {
            'toimipaikka_oid': '1.2.246.562.10.9395737548811',
            'toimintapainotus_koodi': 'tp03',
            'alkamis_pvm': '2017-12-29',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-toiminnallinenpainotus2'
        },
        {
            'toimipaikka_oid': '1.2.246.562.10.6727877596658',
            'toimintapainotus_koodi': 'tp01',
            'alkamis_pvm': '2020-12-29',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-toiminnallinenpainotus3'
        }
    )

    for toiminnallinen_painotus in toiminnallinen_painotus_list:
        _make_post_request('/api/v1/toiminnallisetpainotukset/', toiminnallinen_painotus)

    kielipainotus_list = (
        {
            'toimipaikka_oid': '1.2.246.562.10.9395737548810',
            'kielipainotus_koodi': 'FI',
            'alkamis_pvm': '2017-02-10',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-kielipainotus1'
        },
        {
            'toimipaikka_oid': '1.2.246.562.10.9395737548811',
            'kielipainotus_koodi': 'EN',
            'alkamis_pvm': '2017-12-30',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-kielipainotus2'
        },
        {
            'toimipaikka_oid': '1.2.246.562.10.6727877596658',
            'kielipainotus_koodi': 'SV',
            'alkamis_pvm': '2020-12-30',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-kielipainotus3'
        }
    )

    for kielipainotus in kielipainotus_list:
        _make_post_request('/api/v1/kielipainotukset/', kielipainotus)


def create_henkilot():
    from varda.models import Henkilo
    from varda.misc import hash_string

    # 120456-123C
    Henkilo.objects.create(
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
        vtj_yksiloity=True
    )

    # 010114A0013
    Henkilo.objects.create(
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
        vtj_yksiloity=True
    )

    # 120516A123V
    Henkilo.objects.create(
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
        vtj_yksiloity=True
    )

    # 020476-321F
    Henkilo.objects.create(
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
        vtj_yksiloity=True
    )

    # 120386-109V
    Henkilo.objects.create(
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
        vtj_yksiloity=True
    )

    # 130266-915J
    Henkilo.objects.create(
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
        vtj_yksiloity=True
    )

    # 170334-130B
    Henkilo.objects.create(
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
        vtj_yksiloity=True
    )

    # 110548-316P
    Henkilo.objects.create(
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
        vtj_yksiloity=True
    )

    # 120699-985W
    Henkilo.objects.create(
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
        vtj_yksiloity=True
    )

    Henkilo.objects.create(
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
        vtj_yksiloity=True
    )

    # 220616A322J
    Henkilo.objects.create(
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
        vtj_yksiloity=True
    )

    # 291090-398U
    Henkilo.objects.create(
        henkilotunnus='gAAAAABenaWG3mvY4m1yDf9vOD5kmM6zPAj0Lm9evTQrkRU4AuTEt0PPTmyxBaN7RAvo7HIycpmQzUKsFw-rrSpqwB9z8izObw==',
        henkilotunnus_unique_hash='71759fee33ea6ef42c7c0a064a9369370411d7d9a989fb58148379ee69634862',
        syntyma_pvm='1990-10-29',
        henkilo_oid='1.2.246.562.24.7777777777788',
        etunimet='Mari',
        kutsumanimi='Mari',
        sukunimi='Mairinen',
        aidinkieli_koodi='JA',
        kotikunta_koodi='049',
        turvakielto=False,
        sukupuoli_koodi=2,
        katuosoite='Koivukuja 14',
        postinumero='02101',
        postitoimipaikka='Espoo',
        vtj_yksiloity=True
    )

    # 071119A884T
    Henkilo.objects.create(
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
        vtj_yksiloity=True
    )

    # 291180-7071
    Henkilo.objects.create(
        henkilotunnus='gAAAAABeqDPZvYP3UiGMdjk3DUieipMnFY8yOQ0HgxkukZh9kTYvDmWjzvjZ2BcSQS9mMYWh2YAIQf8NQPkNCNmzmpir_ytkPA==',
        henkilotunnus_unique_hash='da3d4187e11092380164be1feb310544671c1f36d9164db7202340195a91f0c3',
        syntyma_pvm='1990-10-29',
        henkilo_oid='1.2.246.562.24.7777777777755',
        etunimet='Jouni Janne',
        kutsumanimi='Jouni',
        sukunimi='Suroinen',
        aidinkieli_koodi='JA',
        kotikunta_koodi='049',
        turvakielto=False,
        sukupuoli_koodi=2,
        katuosoite='Kannistokatu 14',
        postinumero='02101',
        postitoimipaikka='Espoo',
        vtj_yksiloity=True
    )

    # 010280-952L Huoltaja jolla lapsi 010215A951T
    Henkilo.objects.create(
        henkilotunnus='gAAAAABdiMQHWzMtv1WMLLnWDaiTONIkyMsK5ugZUJm3Ke4d4PR8wLLUs27QVA-iK1t9Lev3zEwCwSbYiSp0Pw_tNix1Hx05mA==',
        henkilotunnus_unique_hash='94d31d49afa408f076996b5ba0317671f185f71b39ac0d1980f341b5b04fb07d',
        syntyma_pvm='1980-03-11',
        henkilo_oid='1.2.246.562.24.99924839517',
        etunimet='Tessa',
        kutsumanimi='Tessa',
        sukunimi='Testilä',
        aidinkieli_koodi='FI',
        kotikunta_koodi='915',
        turvakielto=False,
        sukupuoli_koodi=1,
        katuosoite='Koivukuja 4',
        postinumero='01230',
        postitoimipaikka='Vantaa',
        vtj_yksiloity=True
    )

    # huoltajan lapsi 010215A951T
    Henkilo.objects.create(
        henkilotunnus='gAAAAABdiMQH-7x0FQ8sN7JIIP1bFUgEBpWlqb7-fdHXWXVdpAU6iKR37gQYe48qLrKs-JRNm20gJQMkKNK3tY5nvYSN5y73rw==',
        henkilotunnus_unique_hash='eca80ee4b264ceb572db5a6244bae9c5141400921ec5b80a7d9a2262de495b11',
        syntyma_pvm='2018-03-11',
        henkilo_oid='1.2.246.562.24.86012997950',
        etunimet='Teila Aamu Runelma',
        kutsumanimi='Teila',
        sukunimi='Testilä',
        aidinkieli_koodi='FI',
        kotikunta_koodi='915',
        turvakielto=False,
        sukupuoli_koodi=1,
        katuosoite='Koivukuja 4',
        postinumero='01230',
        postitoimipaikka='Vantaa',
        vtj_yksiloity=True
    )

    # Henkilo (020400A925B) that is a Tyontekija and has a Palvelussuhde and a Tyoskentelypaikka
    Henkilo.objects.create(
        henkilotunnus='gAAAAABe1MWYFHThAaVTNtD0e5eqLrILocRrHLcnWIT3wWY1Q9HL81fFBqT6ZsynVVpG66tY--pZAFVzLTiJkZpeY5ykZWNlYA==',
        henkilotunnus_unique_hash=hash_string('020400A925B'),
        henkilo_oid='1.2.246.562.24.2431884920041',
        etunimet='Aatu',
        kutsumanimi='Aatu',
        sukunimi='Uraputki',
        syntyma_pvm='2000-04-02',
        vtj_yksiloity=True
    )

    # Henkilo (020400A926C) that is a Tyontekija and has two Palvelussuhde
    Henkilo.objects.create(
        henkilotunnus='gAAAAABe1MWYXUPykNlwVdEnV-RGUEIP5SbXSfIMku8S4feee__16334ZkaMohmiiuS0M93jrsgHHFHQHIH2ZG-Rg1bh8w5dqQ==',
        henkilotunnus_unique_hash=hash_string('020400A926C'),
        etunimet='Bella',
        kutsumanimi='Bella',
        sukunimi='Uraputki',
        syntyma_pvm='2000-04-02',
        henkilo_oid='1.2.246.562.24.2431884920042',
        vtj_yksiloity=True
    )

    #  Henkilo (020400A927D) that is a Tyontekija
    Henkilo.objects.create(
        henkilotunnus='gAAAAABe1MWYNPBAkDqIfzXfqNd4bSTi11R3Y8KfyxAlhj0BKnKd1Z0u9oxiIkJ6P-y4QhUHsHB2jo0bbz67-WLDf-HLZK7UOg==',
        henkilotunnus_unique_hash=hash_string('020400A927D'),
        etunimet='Calervo',
        kutsumanimi='Calervo',
        sukunimi='Uraputki',
        syntyma_pvm='2000-04-02',
        henkilo_oid='1.2.246.562.24.2431884920043',
        vtj_yksiloity=True
    )

    # Henkilo (020400A928E) that is a Tyontekija
    Henkilo.objects.create(
        henkilotunnus='gAAAAABgmjjTjdXu61g5n2Dw2r1qt2DRaVDSAXI6SRmn_mhFzB3BNXnbAYWVe3-vUp32xmLV5SjQu8gIqWobPfQDUKr03MatqA==',
        henkilotunnus_unique_hash=hash_string('020400A928E'),
        henkilo_oid='1.2.246.562.24.2431884920044',
        etunimet='Daniella',
        kutsumanimi='Daniella',
        sukunimi='Uraputki',
        syntyma_pvm='2000-04-02',
        vtj_yksiloity=True
    )

    # Henkilo (210700A919U) that is a Tyontekija
    Henkilo.objects.create(
        henkilotunnus='gAAAAABgmjjlIaf4ErPGrrOSqHLrlCHx6bCVbqiFtiDXJZWrSUqh8Dy9y-j0xOqv6be0Afnu75Sp8hZkRYhiNAmzOLfdhWtZlg==',
        henkilotunnus_unique_hash=hash_string('210700A919U'),
        henkilo_oid='1.2.246.562.24.2431884920045',
        etunimet='Döner',
        kutsumanimi='Döner',
        sukunimi='Kebab',
        syntyma_pvm='2000-07-21',
        vtj_yksiloity=True
    )

    # 290116A331A
    Henkilo.objects.create(
        henkilotunnus='gAAAAABey190QZiEOSVXu4lhwaCn5xRAOdf3cwrqVrXHbIA8ToTidxonHNm3hhMQmJYCfe-X3VPQfv577HBlzq08zLrJ7lWtLw==',
        henkilotunnus_unique_hash='d0c2a82170fbb611ed9776dc21d8ed8451077dcb424c6e955c32e08514072e49',
        syntyma_pvm='2016-01-29',
        henkilo_oid='1.2.246.562.24.52864662677',
        etunimet='Mikko',
        kutsumanimi='Mikko',
        sukunimi='Mallikas',
        aidinkieli_koodi='FI',
        kotikunta_koodi='049',
        turvakielto=False,
        sukupuoli_koodi=1,
        katuosoite='Mikontie 15',
        postinumero='12345',
        postitoimipaikka='Espoo',
        vtj_yksiloity=True
    )

    # 260980-642C
    Henkilo.objects.create(
        henkilotunnus='gAAAAABey2Iqol63qQBcaQtLfNlqZWT_4kdqpsLCFBQEMFFdEeMQdZH5Kol2-nDupuLlgbjo7pan-4ozE_559Za7i7FNRaguDw==',
        henkilotunnus_unique_hash='d393febc6ead367a3fa83e44d8df38df492f02821c2b572deb76ebde84fa143b',
        syntyma_pvm='1980-09-26',
        henkilo_oid='1.2.246.562.24.44825558743',
        etunimet='Maija',
        kutsumanimi='Maija',
        sukunimi='Mallikas',
        aidinkieli_koodi='FI',
        kotikunta_koodi='049',
        turvakielto=False,
        sukupuoli_koodi=2,
        katuosoite='Mikontie 15',
        postinumero='12345',
        postitoimipaikka='Espoo',
        vtj_yksiloity=True
    )

    # 010116A807L
    Henkilo.objects.create(
        henkilotunnus='gAAAAABenXh49bqI1Qr_zfwoh9_EVKL3wDkWJY7HnV3anQwzO_cbiuWLsQ1q4yhBTcjeiv9SjxsQmyB5C0A6cGzrBwMdUSGXrQ==',
        henkilotunnus_unique_hash='e56b712fdeeec1887d56a77bfe79a586c2d58352b52ee517b6216589af86a81d',
        syntyma_pvm='2016-01-01',
        henkilo_oid='1.2.246.562.24.6779627637492',
        etunimet='Teppo',
        kutsumanimi='Teppo',
        sukunimi='Tepponen',
        aidinkieli_koodi='FI',
        kotikunta_koodi='405',
        turvakielto=False,
        sukupuoli_koodi=1,
        katuosoite='Kalliokatu 28 B 2',
        postinumero='12345',
        postitoimipaikka='Testilä',
        vtj_yksiloity=True
    )

    # 141117A020X
    Henkilo.objects.create(
        henkilotunnus='gAAAAABenXlgsNb5RnMtGvuteM0wjUe_Dy81APFQLcrq-fToYTeebR_MqgkjfBCqgmoLDHtRUIanaSjLLCbMz0YQS3Fkr8tdLw==',
        henkilotunnus_unique_hash='6131fbc7247d7da4df72ffbce1f878f8b658bb374f71478f344407fb36ca370d',
        syntyma_pvm='2017-11-14',
        henkilo_oid='1.2.246.562.24.4338669286936',
        etunimet='Marjatta',
        kutsumanimi='Marjatta',
        sukunimi='Marjanen',
        aidinkieli_koodi='FI',
        kotikunta_koodi='405',
        turvakielto=False,
        sukupuoli_koodi=2,
        katuosoite='Kalliotie 2 A',
        postinumero='12345',
        postitoimipaikka='Testilä',
        vtj_yksiloity=True
    )

    # 130317A706Y
    Henkilo.objects.create(
        henkilotunnus='gAAAAABenXpOeM3Vwk77oSwDnnAFReTSpJYSd1zXuOqPaScj9dXDaxF0GgqS87I0BzUpN250P77huqN_QZ6Vc_umILmuykGy3Q==',
        henkilotunnus_unique_hash='d1b5e8fe7bea1e5708c298f3d945398e9c567753c5cbd0ac1239e0e523ad5002',
        syntyma_pvm='2017-03-13',
        henkilo_oid='1.2.246.562.24.8925547856499',
        etunimet='Johanna',
        kutsumanimi='Johanna',
        sukunimi='Pekkala',
        aidinkieli_koodi='FI',
        kotikunta_koodi='405',
        turvakielto=False,
        sukupuoli_koodi=2,
        katuosoite='Kallioväylä 3',
        postinumero='12345',
        postitoimipaikka='Testilä',
        vtj_yksiloity=True
    )

    # 120617A273S
    Henkilo.objects.create(
        henkilotunnus='gAAAAABenXr9ZTjOCihMFsN_USeTeQ-GxhOarvvMGgbgknzGf1qthbVPhKTzhRsCvCEuqNkcbPmCIDp7giNDPGQ-13GSEBcnaA==',
        henkilotunnus_unique_hash='ba854e4ffaa6aad557c48c91a8e2d9482a9afe18306ca60538297b03de2a8f84',
        syntyma_pvm='2017-06-12',
        henkilo_oid='1.2.246.562.24.5289462746686',
        etunimet='Timo',
        kutsumanimi='Timo',
        sukunimi='Timonen',
        aidinkieli_koodi='FI',
        kotikunta_koodi='297',
        turvakielto=False,
        sukupuoli_koodi=1,
        katuosoite='Lintukuja 4 A 13',
        postinumero='12345',
        postitoimipaikka='Testilä',
        vtj_yksiloity=True
    )

    # 241217A5155
    Henkilo.objects.create(
        henkilotunnus='gAAAAABenXx0UxAmdYg96djFHoCtRa55tAVZaxBw-exZdc7GCdWqhVwY06r8-3BOZBdNMHnTnJ-7UHYpyUMm_KTAclDJdob5eg==',
        henkilotunnus_unique_hash='346685bbd8d303bdca9f0445cb682962dc80992e89dbffaf75aa003908718284',
        syntyma_pvm='2017-12-24',
        henkilo_oid='1.2.246.562.24.4473262898463',
        etunimet='Taavi',
        kutsumanimi='Taavi',
        sukunimi='Taavetti',
        aidinkieli_koodi='FI',
        kotikunta_koodi='297',
        turvakielto=False,
        sukupuoli_koodi=1,
        katuosoite='Taavintie 4 C 1',
        postinumero='12345',
        postitoimipaikka='Testilä',
        vtj_yksiloity=True
    )

    # 130780-753Y
    Henkilo.objects.create(
        henkilotunnus='gAAAAABenZ_1sORkNH6zABta2uQ8sV934GEnO3coo2UrJrOYoGiJEyCQKJRYD-Yx6d_ez0l4Vi9Bv9gt7FWdR14Ec4tTwPStow==',
        henkilotunnus_unique_hash='b9496e91fcd1f21558b80030c87b9dd01bacff5a28593b3bbe2885a8968e2a2a',
        syntyma_pvm='1980-07-13',
        henkilo_oid='1.2.246.562.24.2434693467574',
        etunimet='Taneli',
        kutsumanimi='Taneli',
        sukunimi='Tattinen',
        aidinkieli_koodi='FI',
        kotikunta_koodi='405',
        turvakielto=False,
        sukupuoli_koodi=1,
        katuosoite='Kalliokatu 28 B 2',
        postinumero='12345',
        postitoimipaikka='Testilä',
        vtj_yksiloity=True
    )

    # 010177-0520
    Henkilo.objects.create(
        henkilotunnus='gAAAAABenaDaqT29a4sEhdR81vox-mOxW-JU_al1t3vHgqITdvvgZhY1tafdboKuzWbjVRoDKTLgumsBIfMcV_eBZlQz1d-8yg==',
        henkilotunnus_unique_hash='db98de5bffe5ad70633547c1bf909066547e12d0f3f6f4619d5e18a30563c9ab',
        syntyma_pvm='1977-01-01',
        henkilo_oid='1.2.246.562.24.3367432256266',
        etunimet='Kirsi',
        kutsumanimi='Kirsi',
        sukunimi='Taavetti',
        aidinkieli_koodi='FI',
        kotikunta_koodi='405',
        turvakielto=False,
        sukupuoli_koodi=2,
        katuosoite='Kalliokatu 28 B 2',
        postinumero='12345',
        postitoimipaikka='Testilä',
        vtj_yksiloity=True
    )

    # 241093-031J
    Henkilo.objects.create(
        henkilotunnus='gAAAAABenaGQh-7GdNDjqp2fpEKrmSfn7JJXkhKJOSkE5WIvHnax4g7bfHAj7Wzs5TA-NRl6J1sgYbSyktpweClcENeUrrmRjw==',
        henkilotunnus_unique_hash='20a1d791974eee539e683b94a85b45055a25130353e6255ac929caed5e71283a',
        syntyma_pvm='1993-10-24',
        henkilo_oid='1.2.246.562.24.2395579772672',
        etunimet='Kalle Kalevi',
        kutsumanimi='Kalle',
        sukunimi='Kumpunen',
        aidinkieli_koodi='FI',
        kotikunta_koodi='297',
        turvakielto=False,
        sukupuoli_koodi=1,
        katuosoite='Taavintie 4 C 1',
        postinumero='12345',
        postitoimipaikka='Testilä',
        vtj_yksiloity=True
    )

    # 240219A149T
    Henkilo.objects.create(
        henkilotunnus='gAAAAABfK90_SFbRRu7lXJaLvCe4SJMVG_oOdr1Ui8aSwWDNoTVLUqU-lWcceHV9LEQVN4TlSJhv2frKjrbyCokPLTyA1X-3hg==',
        henkilotunnus_unique_hash='5d92e7c9f631645e2e86e6636cb4f5ba270557f4ee27118ae1884fc354e2db1a',
        syntyma_pvm='1993-10-24',
        henkilo_oid='1.2.246.562.24.2395579772673',
        etunimet='Pentti Jr',
        kutsumanimi='Pentti',
        sukunimi='Kivimäki',
        aidinkieli_koodi='FI',
        kotikunta_koodi='297',
        turvakielto=False,
        sukupuoli_koodi=1,
        katuosoite='Taavintie 4 C 1',
        postinumero='12345',
        postitoimipaikka='Testilä',
        vtj_yksiloity=True
    )

    # 271020A212F
    Henkilo.objects.create(
        henkilotunnus='gAAAAABgT2zNnKt87-rBEeT9epdXTjvF67Yk7q4-qDrO6FW1d4MgJFT6djQ0QY-QWHgIIoticjgwvznBky69_boDFwv3B3R_Nw==',
        henkilotunnus_unique_hash='8cea74b21e513e051399bd00b864af7184e03c814d92dee55172e3928dd541ab',
        syntyma_pvm='2020-10-27',
        henkilo_oid='1.2.246.562.24.2395579779541',
        etunimet='Anni',
        kutsumanimi='Anni',
        sukunimi='Testinen',
        aidinkieli_koodi='FI',
        kotikunta_koodi='297',
        turvakielto=False,
        sukupuoli_koodi=2,
        katuosoite='Tukkarinkatu 4c',
        postinumero='12345',
        postitoimipaikka='Testilä',
        vtj_yksiloity=True
    )

    # 150245-855F
    Henkilo.objects.create(
        henkilotunnus='gAAAAABgYvUVMwshLRtdsBOCLPqktBTxb_HMypCYWvfoXcxp7Ahx5EskuAofNCBB1fGQ012JvK0ClIhZ8XbLCdHqgQfA96xVMQ==',
        henkilotunnus_unique_hash='c51885f0950edc6f5b10e17245a582779726456231c7d037f112601026b4ca36',
        syntyma_pvm='1945-02-15',
        henkilo_oid='1.2.246.562.24.4645229637988',
        etunimet='Jere',
        kutsumanimi='Jere',
        sukunimi='Duunari',
        aidinkieli_koodi='FI',
        kotikunta_koodi='297',
        turvakielto=False,
        sukupuoli_koodi=1,
        katuosoite='Duunarintie 1 A',
        postinumero='12345',
        postitoimipaikka='Testilä',
        vtj_yksiloity=True
    )

    # 100646-792P
    Henkilo.objects.create(
        henkilotunnus='gAAAAABgYvZtPK_je4Kbb_dt0bQI3jlNe5WT1XZ0W-XpFJHE0xbZspbsdjzmyaPLF4Kpy1WwufGwdcvctXsCtEXssn-0x04qJQ==',
        henkilotunnus_unique_hash='dabac6822ee363c876261b5a043aca127af7924767c4df22e5b61658206dd50d',
        syntyma_pvm='1946-06-10',
        henkilo_oid='1.2.246.562.24.5826267847674',
        etunimet='Julia',
        kutsumanimi='Julia',
        sukunimi='Duunari',
        aidinkieli_koodi='FI',
        kotikunta_koodi='297',
        turvakielto=False,
        sukupuoli_koodi=1,
        katuosoite='Duunarintie 1 A',
        postinumero='12345',
        postitoimipaikka='Testilä',
        vtj_yksiloity=True
    )


def _create_lapsi_and_related_data(lapsi, huoltaja_list=(), vakapaatos_list=(), maksutieto_list=()):
    from django.db.models import Q
    from varda.constants import HETU_REGEX
    from varda.misc import hash_string
    from varda.models import Huoltaja, Henkilo, Huoltajuussuhde

    resp_lapsi = _make_post_request('/api/v1/lapset/', lapsi)
    lapsi_id = json.loads(resp_lapsi.content)['id']

    for huoltaja_identifier in huoltaja_list:
        huoltaja_filter = (Q(henkilotunnus_unique_hash=hash_string(huoltaja_identifier))
                           if HETU_REGEX.fullmatch(huoltaja_identifier)
                           else Q(henkilo_oid=huoltaja_identifier))
        huoltaja_obj = Huoltaja.objects.get_or_create(henkilo=Henkilo.objects.get(huoltaja_filter))[0]
        Huoltajuussuhde.objects.get_or_create(huoltaja=huoltaja_obj, lapsi_id=lapsi_id,
                                              defaults={'voimassa_kytkin': True})

    for vakapaatos in vakapaatos_list:
        vakapaatos_dict = vakapaatos[0]
        vakasuhde_list = vakapaatos[1]

        vakapaatos_dict['lapsi'] = f'/api/v1/lapset/{lapsi_id}/'
        resp_vakapaatos = _make_post_request('/api/v1/varhaiskasvatuspaatokset/', vakapaatos_dict)
        vakapaatos_id = json.loads(resp_vakapaatos.content)['id']

        for vakasuhde in vakasuhde_list:
            vakasuhde['varhaiskasvatuspaatos'] = f'/api/v1/varhaiskasvatuspaatokset/{vakapaatos_id}/'
            _make_post_request('/api/v1/varhaiskasvatussuhteet/', vakasuhde)

    for maksutieto in maksutieto_list:
        maksutieto['lapsi'] = f'/api/v1/lapset/{lapsi_id}/'
        _make_post_request('/api/v1/maksutiedot/', maksutieto)


def create_lapset():
    from varda.models import Varhaiskasvatussuhde

    _create_lapsi_and_related_data(
        {
            'henkilo_oid': '1.2.246.562.24.47279942650',
            'vakatoimija_oid': '1.2.246.562.10.93957375488',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-lapsi1'
        },
        huoltaja_list=('1.2.987654321', '120386-109V',),
        vakapaatos_list=(
            (
                {
                    'vuorohoito_kytkin': False,
                    'pikakasittely_kytkin': False,
                    'tuntimaara_viikossa': 37.5,
                    'paivittainen_vaka_kytkin': False,
                    'kokopaivainen_vaka_kytkin': False,
                    'tilapainen_vaka_kytkin': False,
                    'jarjestamismuoto_koodi': 'jm04',
                    'hakemus_pvm': '2017-01-12',
                    'alkamis_pvm': '2017-02-11',
                    'paattymis_pvm': '2022-02-24',
                    'lahdejarjestelma': '1',
                    'tunniste': 'testing-varhaiskasvatuspaatos1'
                },
                (
                    {
                        'toimipaikka_oid': '1.2.246.562.10.9395737548810',
                        'alkamis_pvm': '2017-02-11',
                        'paattymis_pvm': '2020-02-24',
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-varhaiskasvatussuhde1'
                    },
                ),
            ),
        ),
        maksutieto_list=(
            {
                'huoltajat': [
                    {'henkilo_oid': '1.2.987654321', 'etunimet': 'Pauliina', 'sukunimi': 'Virtanen'},
                    {'henkilotunnus': '120386-109V', 'etunimet': 'Pertti', 'sukunimi': 'Virtanen'}
                ],
                'maksun_peruste_koodi': 'mp01',
                'palveluseteli_arvo': 0.00,
                'asiakasmaksu': 0.00,
                'perheen_koko': 3,
                'alkamis_pvm': '2019-09-01',
                'lahdejarjestelma': '1',
                'tunniste': 'testing-maksutieto1'
            },
            {
                'huoltajat': [{'henkilotunnus': '120386-109V', 'etunimet': 'Pertti', 'sukunimi': 'Virtanen'}],
                'maksun_peruste_koodi': 'mp03',
                'palveluseteli_arvo': 100,
                'asiakasmaksu': 150,
                'perheen_koko': 2,
                'alkamis_pvm': '2019-09-01',
                'lahdejarjestelma': '1',
                'tunniste': 'testing-maksutieto3'
            },
        )
    )
    _create_lapsi_and_related_data(
        {
            'henkilo_oid': '1.2.246.562.24.58672764848',
            'vakatoimija_oid': '1.2.246.562.10.93957375488',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-lapsi2'
        },
        huoltaja_list=('120386-109V',),
        vakapaatos_list=(
            (
                {
                    'vuorohoito_kytkin': False,
                    'pikakasittely_kytkin': False,
                    'tuntimaara_viikossa': 40.0,
                    'paivittainen_vaka_kytkin': True,
                    'kokopaivainen_vaka_kytkin': True,
                    'tilapainen_vaka_kytkin': False,
                    'jarjestamismuoto_koodi': 'jm04',
                    'hakemus_pvm': '2018-09-05',
                    'alkamis_pvm': '2018-09-05',
                    'lahdejarjestelma': '1',
                    'tunniste': 'testing-varhaiskasvatuspaatos2'
                },
                (
                    {
                        'toimipaikka_oid': '1.2.246.562.10.9395737548810',
                        'alkamis_pvm': '2018-09-05',
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-varhaiskasvatussuhde2'
                    },
                ),
            ),
        )
    )
    _create_lapsi_and_related_data(
        {
            'henkilo_oid': '1.2.246.562.24.49084901392',
            'vakatoimija_oid': '1.2.246.562.10.34683023489',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-lapsi3'
        },
        huoltaja_list=('120386-109V',),
        vakapaatos_list=(
            (
                {
                    'vuorohoito_kytkin': False,
                    'pikakasittely_kytkin': False,
                    'tuntimaara_viikossa': 39.0,
                    'paivittainen_vaka_kytkin': True,
                    'kokopaivainen_vaka_kytkin': True,
                    'tilapainen_vaka_kytkin': False,
                    'jarjestamismuoto_koodi': 'jm01',
                    'hakemus_pvm': '2018-09-05',
                    'alkamis_pvm': '2018-09-05',
                    'lahdejarjestelma': '1',
                    'tunniste': 'testing-varhaiskasvatuspaatos3'
                },
                (
                    {
                        'toimipaikka_oid': '1.2.246.562.10.9395737548815',
                        'alkamis_pvm': '2018-09-05',
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-varhaiskasvatussuhde3'
                    },
                ),
            ),
        ),
        maksutieto_list=(
            {
                'huoltajat': [{'henkilotunnus': '120386-109V', 'etunimet': 'Pertti', 'sukunimi': 'Virtanen'}],
                'maksun_peruste_koodi': 'mp02',
                'palveluseteli_arvo': 150,
                'asiakasmaksu': 0,
                'perheen_koko': 3,
                'alkamis_pvm': '2019-09-01',
                'paattymis_pvm': '2025-01-01',
                'lahdejarjestelma': '1',
                'tunniste': 'testing-maksutieto2'
            },
        )
    )
    _create_lapsi_and_related_data(
        {
            'henkilo_oid': '1.2.246.562.24.6815981182311',
            'oma_organisaatio_oid': '1.2.246.562.10.34683023489',
            'paos_organisaatio_oid': '1.2.246.562.10.93957375488',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-lapsi4'
        },
        huoltaja_list=('110548-316P',),
        vakapaatos_list=(
            (
                {
                    'vuorohoito_kytkin': False,
                    'pikakasittely_kytkin': False,
                    'tuntimaara_viikossa': 39.0,
                    'paivittainen_vaka_kytkin': True,
                    'kokopaivainen_vaka_kytkin': True,
                    'tilapainen_vaka_kytkin': False,
                    'jarjestamismuoto_koodi': 'jm03',
                    'hakemus_pvm': '2018-09-05',
                    'alkamis_pvm': '2018-09-05',
                    'lahdejarjestelma': '1',
                    'tunniste': 'testing-varhaiskasvatuspaatos4'
                },
                (
                    {
                        'toimipaikka_oid': '1.2.246.562.10.9395737548817',
                        'alkamis_pvm': '2018-09-05',
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-varhaiskasvatussuhde4'
                    },
                    {
                        'toimipaikka_oid': '1.2.246.562.10.9395737548817',
                        'alkamis_pvm': '2021-01-05',
                        'paattymis_pvm': '2022-01-03',
                        'lahdejarjestelma': '1',
                        'tunniste': 'kela_testing_jm03'
                    },
                ),
            ),
        )
    )
    _create_lapsi_and_related_data(
        {
            'henkilo_oid': '1.2.246.562.24.7777777777777',
            'oma_organisaatio_oid': '1.2.246.562.10.93957375484',
            'paos_organisaatio_oid': '1.2.246.562.10.93957375488',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-lapsi5'
        },
        huoltaja_list=('1.2.246.562.24.7777777777788',),
        vakapaatos_list=(
            (
                {
                    'vuorohoito_kytkin': False,
                    'pikakasittely_kytkin': False,
                    'tuntimaara_viikossa': 39.0,
                    'paivittainen_vaka_kytkin': True,
                    'kokopaivainen_vaka_kytkin': True,
                    'tilapainen_vaka_kytkin': False,
                    'jarjestamismuoto_koodi': 'jm03',
                    'hakemus_pvm': '2018-10-05',
                    'alkamis_pvm': '2018-10-05',
                    'lahdejarjestelma': '1',
                    'tunniste': 'testing-varhaiskasvatuspaatos5'
                },
                (
                    {
                        'toimipaikka_oid': '1.2.246.562.10.9395737548817',
                        'alkamis_pvm': '2018-10-05',
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-varhaiskasvatussuhde5'
                    },
                ),
            ),
        ),
        maksutieto_list=(
            {
                'huoltajat': [
                    {'henkilo_oid': '1.2.246.562.24.7777777777788', 'etunimet': 'Mari', 'sukunimi': 'Mairinen'}
                ],
                'maksun_peruste_koodi': 'mp03',
                'palveluseteli_arvo': 100,
                'asiakasmaksu': 150,
                'perheen_koko': 2,
                'alkamis_pvm': '2019-09-01',
                'lahdejarjestelma': '1',
                'tunniste': 'testing-maksutieto4'
            },
        )
    )
    _create_lapsi_and_related_data(
        {
            'henkilo_oid': '1.2.246.562.24.86012997950',
            'vakatoimija_oid': '1.2.246.562.10.34683023489',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-lapsi6'
        },
        huoltaja_list=('1.2.246.562.24.99924839517',),
        vakapaatos_list=(
            (
                {
                    'vuorohoito_kytkin': True,
                    'pikakasittely_kytkin': True,
                    'tuntimaara_viikossa': 37.5,
                    'paivittainen_vaka_kytkin': None,
                    'kokopaivainen_vaka_kytkin': None,
                    'tilapainen_vaka_kytkin': False,
                    'jarjestamismuoto_koodi': 'jm01',
                    'hakemus_pvm': '2019-01-01',
                    'alkamis_pvm': '2019-02-11',
                    'paattymis_pvm': '2019-10-24',
                    'lahdejarjestelma': '1',
                    'tunniste': 'testing-varhaiskasvatuspaatos6'
                },
                (
                    {
                        'toimipaikka_oid': '1.2.246.562.10.9395737548815',
                        'alkamis_pvm': '2019-02-11',
                        'paattymis_pvm': '2019-02-24',
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-varhaiskasvatussuhde6'
                    },
                ),
            ),
        )
    )
    _create_lapsi_and_related_data(
        {
            'henkilo_oid': '1.2.246.562.24.86012997950',
            'vakatoimija_oid': '1.2.246.562.10.93957375488',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-lapsi7'
        },
        huoltaja_list=('1.2.246.562.24.99924839517',),
        vakapaatos_list=(
            (
                {
                    'vuorohoito_kytkin': False,
                    'pikakasittely_kytkin': True,
                    'tuntimaara_viikossa': 30.5,
                    'paivittainen_vaka_kytkin': True,
                    'kokopaivainen_vaka_kytkin': False,
                    'tilapainen_vaka_kytkin': False,
                    'jarjestamismuoto_koodi': 'jm04',
                    'hakemus_pvm': '2018-01-01',
                    'alkamis_pvm': '2018-01-11',
                    'paattymis_pvm': '2020-02-01',
                    'lahdejarjestelma': '1',
                    'tunniste': 'testing-varhaiskasvatuspaatos7'
                },
                (
                    {
                        'toimipaikka_oid': '1.2.246.562.10.9395737548811',
                        'alkamis_pvm': '2018-09-05',
                        'paattymis_pvm': '2020-01-20',
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-varhaiskasvatussuhde7'
                    },
                    {
                        'toimipaikka_oid': '1.2.246.562.10.9395737548810',
                        'alkamis_pvm': '2018-05-01',
                        'paattymis_pvm': '2020-01-24',
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-varhaiskasvatussuhde8'
                    }
                ),
            ),
        )
    )
    _create_lapsi_and_related_data(
        {
            'henkilo_oid': '1.2.246.562.24.86012997950',
            'oma_organisaatio_oid': '1.2.246.562.10.34683023489',
            'paos_organisaatio_oid': '1.2.246.562.10.93957375488',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-lapsi8'
        },
        huoltaja_list=('1.2.246.562.24.99924839517',),
        vakapaatos_list=(
            (
                {
                    'vuorohoito_kytkin': False,
                    'pikakasittely_kytkin': False,
                    'tuntimaara_viikossa': 39.0,
                    'paivittainen_vaka_kytkin': True,
                    'kokopaivainen_vaka_kytkin': True,
                    'tilapainen_vaka_kytkin': False,
                    'jarjestamismuoto_koodi': 'jm03',
                    'hakemus_pvm': '2018-10-05',
                    'alkamis_pvm': '2018-10-05',
                    'lahdejarjestelma': '1',
                    'tunniste': 'testing-varhaiskasvatuspaatos9'
                },
                (
                    {
                        'toimipaikka_oid': '1.2.246.562.10.9395737548817',
                        'alkamis_pvm': '2019-11-11',
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-varhaiskasvatussuhde9'
                    },
                ),
            ),
        )
    )
    _create_lapsi_and_related_data(
        {
            'henkilo_oid': '1.2.246.562.24.86012997950',
            'vakatoimija_oid': '1.2.246.562.10.93957375484',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-lapsi9'
        },
        vakapaatos_list=(
            (
                {
                    'vuorohoito_kytkin': False,
                    'pikakasittely_kytkin': True,
                    'tuntimaara_viikossa': 30.5,
                    'paivittainen_vaka_kytkin': True,
                    'kokopaivainen_vaka_kytkin': False,
                    'tilapainen_vaka_kytkin': False,
                    'jarjestamismuoto_koodi': 'jm01',
                    'hakemus_pvm': '2019-01-01',
                    'alkamis_pvm': '2019-11-11',
                    'paattymis_pvm': '2019-12-22',
                    'lahdejarjestelma': '1',
                    'tunniste': 'testing-varhaiskasvatuspaatos8'
                },
                (),  # no vakasuhde to test huoltajanlapsi error situations
            ),
        )
    )
    _create_lapsi_and_related_data(
        {
            'henkilo_oid': '1.2.246.562.24.52864662677',
            'vakatoimija_oid': '1.2.246.562.10.93957375488',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-lapsi10'
        },
        huoltaja_list=('1.2.246.562.24.44825558743',),
        vakapaatos_list=(
            (
                {
                    'vuorohoito_kytkin': False,
                    'pikakasittely_kytkin': False,
                    'tuntimaara_viikossa': 39.0,
                    'paivittainen_vaka_kytkin': True,
                    'kokopaivainen_vaka_kytkin': True,
                    'tilapainen_vaka_kytkin': False,
                    'jarjestamismuoto_koodi': 'jm05',
                    'hakemus_pvm': '2020-04-01',
                    'alkamis_pvm': '2020-04-15',
                    'lahdejarjestelma': '1',
                    'tunniste': 'testing-varhaiskasvatuspaatos10'
                },
                (
                    {
                        'toimipaikka_oid': '1.2.246.562.10.2935996863483',
                        'alkamis_pvm': '2020-05-01',
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-varhaiskasvatussuhde10'
                    },
                ),
            ),
            (
                {
                    'vuorohoito_kytkin': False,
                    'pikakasittely_kytkin': False,
                    'tuntimaara_viikossa': 39.0,
                    'paivittainen_vaka_kytkin': True,
                    'kokopaivainen_vaka_kytkin': True,
                    'tilapainen_vaka_kytkin': False,
                    'jarjestamismuoto_koodi': 'jm05',
                    'hakemus_pvm': '2021-04-01',
                    'alkamis_pvm': '2021-04-05',
                    'lahdejarjestelma': '1',
                    'tunniste': 'testing-varhaiskasvatuspaatos_kela_private'
                },
                (
                    {
                        'toimipaikka_oid': '1.2.246.562.10.9395737548817',
                        'alkamis_pvm': '2021-04-05',
                        'paattymis_pvm': '2021-04-15',
                        'lahdejarjestelma': '1',
                        'tunniste': 'kela_testing_private'
                    },
                ),
            ),
        ),
        maksutieto_list=(
            {
                'huoltajat': [
                    {'henkilo_oid': '1.2.246.562.24.44825558743', 'etunimet': 'Maija', 'sukunimi': 'Mallikas'}
                ],
                'maksun_peruste_koodi': 'mp03',
                'palveluseteli_arvo': 0.00,
                'asiakasmaksu': 150,
                'alkamis_pvm': '2020-05-20',
                'lahdejarjestelma': '1',
                'tunniste': 'testing-maksutieto5'
            },
        )
    )
    _create_lapsi_and_related_data(
        {
            'henkilo_oid': '1.2.246.562.24.6779627637492',
            'vakatoimija_oid': '1.2.246.562.10.57294396385',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-lapsi11'
        },
        huoltaja_list=('1.2.246.562.24.2434693467574', '1.2.246.562.24.3367432256266',),
        vakapaatos_list=(
            (
                {
                    'vuorohoito_kytkin': False,
                    'pikakasittely_kytkin': False,
                    'tuntimaara_viikossa': 37.5,
                    'paivittainen_vaka_kytkin': True,
                    'kokopaivainen_vaka_kytkin': True,
                    'tilapainen_vaka_kytkin': False,
                    'jarjestamismuoto_koodi': 'jm01',
                    'hakemus_pvm': '2019-09-05',
                    'alkamis_pvm': '2019-09-06',
                    'lahdejarjestelma': '1',
                    'tunniste': 'testing-varhaiskasvatuspaatos11'
                },
                (
                    {
                        'toimipaikka_oid': '1.2.246.562.10.6727877596658',
                        'alkamis_pvm': '2019-10-05',
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-varhaiskasvatussuhde11'
                    },
                ),
            ),
        ),
        maksutieto_list=(
            {
                'huoltajat': [
                    {'henkilo_oid': '1.2.246.562.24.2434693467574', 'etunimet': 'Taneli', 'sukunimi': 'Tattinen'},
                    {'henkilo_oid': '1.2.246.562.24.3367432256266', 'etunimet': 'Kirsi', 'sukunimi': 'Taavetti'}
                ],
                'maksun_peruste_koodi': 'mp03',
                'palveluseteli_arvo': 0.00,
                'asiakasmaksu': 50.00,
                'perheen_koko': 3,
                'alkamis_pvm': '2020-01-11',
                'lahdejarjestelma': '1',
                'tunniste': 'testing-maksutieto6'
            },
        )
    )
    _create_lapsi_and_related_data(
        {
            'henkilo_oid': '1.2.246.562.24.4338669286936',
            'vakatoimija_oid': '1.2.246.562.10.57294396385',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-lapsi12'
        },
        vakapaatos_list=(
            (
                {
                    'vuorohoito_kytkin': False,
                    'pikakasittely_kytkin': False,
                    'tuntimaara_viikossa': 37.5,
                    'paivittainen_vaka_kytkin': True,
                    'kokopaivainen_vaka_kytkin': True,
                    'tilapainen_vaka_kytkin': False,
                    'jarjestamismuoto_koodi': 'jm01',
                    'hakemus_pvm': '2019-10-05',
                    'alkamis_pvm': '2019-11-06',
                    'lahdejarjestelma': '1',
                    'tunniste': 'testing-varhaiskasvatuspaatos12'
                },
                (
                    {
                        'toimipaikka_oid': '1.2.246.562.10.6727877596658',
                        'alkamis_pvm': '2019-12-12',
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-varhaiskasvatussuhde12'
                    },
                ),
            ),
        )
    )
    _create_lapsi_and_related_data(
        {
            'henkilo_oid': '1.2.246.562.24.8925547856499',
            'vakatoimija_oid': '1.2.246.562.10.57294396385',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-lapsi13'
        },
        vakapaatos_list=(
            (
                {
                    'vuorohoito_kytkin': False,
                    'pikakasittely_kytkin': False,
                    'tuntimaara_viikossa': 39.0,
                    'paivittainen_vaka_kytkin': True,
                    'kokopaivainen_vaka_kytkin': True,
                    'tilapainen_vaka_kytkin': False,
                    'jarjestamismuoto_koodi': 'jm01',
                    'hakemus_pvm': '2020-01-01',
                    'alkamis_pvm': '2020-01-02',
                    'lahdejarjestelma': '1',
                    'tunniste': 'testing-varhaiskasvatuspaatos13'
                },
                (
                    {
                        'toimipaikka_oid': '1.2.246.562.10.2565458382544',
                        'alkamis_pvm': '2020-02-05',
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-varhaiskasvatussuhde13'
                    },
                ),
            ),
        )
    )
    _create_lapsi_and_related_data(
        {
            'henkilo_oid': '1.2.246.562.24.5289462746686',
            'vakatoimija_oid': '1.2.246.562.10.52966755795',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-lapsi14'
        },
        huoltaja_list=('1.2.246.562.24.2395579772672',),
        vakapaatos_list=(
            (
                {
                    'vuorohoito_kytkin': False,
                    'pikakasittely_kytkin': False,
                    'tuntimaara_viikossa': 30.0,
                    'paivittainen_vaka_kytkin': True,
                    'kokopaivainen_vaka_kytkin': True,
                    'tilapainen_vaka_kytkin': False,
                    'jarjestamismuoto_koodi': 'jm01',
                    'hakemus_pvm': '2020-03-03',
                    'alkamis_pvm': '2020-03-03',
                    'lahdejarjestelma': '1',
                    'tunniste': 'testing-varhaiskasvatuspaatos14'
                },
                (
                    {
                        'toimipaikka_oid': '1.2.246.562.10.9625978384762',
                        'alkamis_pvm': '2020-04-01',
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-varhaiskasvatussuhde14'
                    },
                ),
            ),
        ),
        maksutieto_list=(
            {
                'huoltajat': [
                    {'henkilo_oid': '1.2.246.562.24.2395579772672', 'etunimet': 'Kalle Kalevi', 'sukunimi': 'Kumpunen'}
                ],
                'maksun_peruste_koodi': 'mp03',
                'palveluseteli_arvo': 0.00,
                'asiakasmaksu': 55.00,
                'perheen_koko': 4,
                'alkamis_pvm': '2020-03-11',
                'lahdejarjestelma': '1',
                'tunniste': 'testing-maksutieto7'
            },
        )
    )
    _create_lapsi_and_related_data(
        {
            'henkilo_oid': '1.2.246.562.24.4473262898463',
            'vakatoimija_oid': '1.2.246.562.10.52966755795',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-lapsi15'
        },
        vakapaatos_list=(
            (
                {
                    'vuorohoito_kytkin': False,
                    'pikakasittely_kytkin': False,
                    'tuntimaara_viikossa': 35.5,
                    'paivittainen_vaka_kytkin': True,
                    'kokopaivainen_vaka_kytkin': True,
                    'tilapainen_vaka_kytkin': False,
                    'jarjestamismuoto_koodi': 'jm01',
                    'hakemus_pvm': '2019-09-30',
                    'alkamis_pvm': '2019-09-30',
                    'lahdejarjestelma': '1',
                    'tunniste': 'testing-varhaiskasvatuspaatos15'
                },
                (
                    {
                        'toimipaikka_oid': '1.2.246.562.10.9625978384762',
                        'alkamis_pvm': '2020-01-10',
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-varhaiskasvatussuhde15'
                    },
                ),
            ),
        )
    )
    _create_lapsi_and_related_data(
        {
            'henkilo_oid': '1.2.246.562.24.2395579779541',
            'vakatoimija_oid': '1.2.246.562.10.34683023489',
            'lahdejarjestelma': '1',
            'tunniste': 'lapsi_tilapainen_vaka'
        },
        vakapaatos_list=(
            (
                {
                    'vuorohoito_kytkin': False,
                    'pikakasittely_kytkin': False,
                    'tuntimaara_viikossa': 35.5,
                    'paivittainen_vaka_kytkin': True,
                    'kokopaivainen_vaka_kytkin': True,
                    'tilapainen_vaka_kytkin': True,
                    'jarjestamismuoto_koodi': 'jm01',
                    'hakemus_pvm': '2021-09-25',
                    'alkamis_pvm': '2021-09-25',
                    'paattymis_pvm': '2021-10-02',
                    'lahdejarjestelma': '1',
                    'tunniste': 'testing-varhaiskasvatuspaatos_kela_tilapainen'
                },
                (
                    {
                        'toimipaikka_oid': '1.2.246.562.10.9395737548815',
                        'alkamis_pvm': '2021-09-30',
                        'paattymis_pvm': '2021-10-02',
                        'lahdejarjestelma': '1',
                        'tunniste': 'kela_testing_public_tilapainen'
                    },
                ),
            ),
        )
    )

    kela_testing_vakasuhteet = (Varhaiskasvatussuhde.objects
                                .filter(tunniste__in=('kela_testing_jm03', 'testing-varhaiskasvatussuhde4',
                                                      'testing-varhaiskasvatussuhde3',)))
    for vakasuhde in kela_testing_vakasuhteet:
        vakasuhde.luonti_pvm = '2021-01-04 00:00:00.00000+02'
        vakasuhde.muutos_pvm = '2021-01-04 00:00:00.00000+02'
        vakasuhde.save()

        historical_vakasuhde = Varhaiskasvatussuhde.history.get(id=vakasuhde.id, history_type='+')
        historical_vakasuhde.luonti_pvm = '2021-01-04 00:00:00.00000+02'
        historical_vakasuhde.muutos_pvm = '2021-01-04 00:00:00.00000+02'
        historical_vakasuhde.history_date = '2021-01-04 00:00:00.00000+02'
        historical_vakasuhde.save()


def create_paos_toiminta():
    paos_toiminta_list = (
        {
            'oma_organisaatio_oid': '1.2.246.562.10.93957375488',
            'paos_organisaatio_oid': '1.2.246.562.10.34683023489',
        },
        {
            'oma_organisaatio_oid': '1.2.246.562.10.34683023489',
            'paos_toimipaikka_oid': '1.2.246.562.10.9395737548817',
        },
        {
            'oma_organisaatio_oid': '1.2.246.562.10.93957375484',
            'paos_organisaatio_oid': '1.2.246.562.10.34683023489',
        },
        {
            'oma_organisaatio_oid': '1.2.246.562.10.34683023489',
            'paos_toimipaikka_oid': '1.2.246.562.10.9395737548812',
        },
        {
            'oma_organisaatio_oid': '1.2.246.562.10.93957375488',
            'paos_organisaatio_oid': '1.2.246.562.10.93957375484',
        },
        {
            'oma_organisaatio_oid': '1.2.246.562.10.93957375484',
            'paos_toimipaikka_oid': '1.2.246.562.10.9395737548817',
        }
    )

    for paos_toiminta in paos_toiminta_list:
        _make_post_request('/api/v1/paos-toiminnat/', paos_toiminta)


def create_user_data():
    from django.contrib.auth.models import User
    from varda.models import Z3_AdditionalCasUserFields, Z4_CasKayttoOikeudet

    tester_user = User.objects.get(username='tester')
    tester2_user = User.objects.get(username='tester2')
    tester3_user = User.objects.get(username='tester3')
    tester6_user = User.objects.get(username='huoltajatietojen_tallentaja')
    tester7_user = User.objects.get(username='tester7')
    tester8_user = User.objects.get(username='tester8')
    tester9_user = User.objects.get(username='tester9')
    tester10_user = User.objects.get(username='tester10')

    pk_vakajarjestaja_1_user = User.objects.get(username='pkvakajarjestaja1')
    pk_vakajarjestaja_2_user = User.objects.get(username='pkvakajarjestaja2')

    Z3_AdditionalCasUserFields.objects.create(
        user_id=tester_user.id,
        kayttajatyyppi='VIRKAILIJA',
        henkilo_oid='1.2.345678910',
        asiointikieli_koodi='sv',
        last_modified='2019-01-24 12:00:00+1459'
    )

    Z3_AdditionalCasUserFields.objects.create(
        user_id=tester2_user.id,
        kayttajatyyppi='VIRKAILIJA',
        henkilo_oid='1.2.246.562.24.6722258949565',
        asiointikieli_koodi='fi',
        last_modified='2019-01-24 12:00:00+1459'
    )

    Z3_AdditionalCasUserFields.objects.create(
        user_id=tester3_user.id,
        kayttajatyyppi='VIRKAILIJA',
        henkilo_oid='',
        asiointikieli_koodi='fi',
        last_modified='2020-10-06 12:00:00+1459'
    )

    Z3_AdditionalCasUserFields.objects.create(
        user_id=tester6_user.id,
        kayttajatyyppi='VIRKAILIJA',
        henkilo_oid='1.2.345678001',
        asiointikieli_koodi='fi',
        last_modified='2019-01-24 12:00:00+1459'
    )

    Z3_AdditionalCasUserFields.objects.create(
        user_id=tester7_user.id,
        kayttajatyyppi='VIRKAILIJA',
        henkilo_oid='1.2.345679001',
        asiointikieli_koodi='fi',
        last_modified='2019-01-24 12:00:00+1459'
    )

    Z3_AdditionalCasUserFields.objects.create(
        user_id=tester8_user.id,
        kayttajatyyppi='VIRKAILIJA',
        henkilo_oid='',
        asiointikieli_koodi='fi',
        last_modified='2019-01-24 12:00:00+1459'
    )

    Z3_AdditionalCasUserFields.objects.create(
        user_id=tester9_user.id,
        kayttajatyyppi='VIRKAILIJA',
        henkilo_oid='1.2.345680001',
        asiointikieli_koodi='fi',
        last_modified='2019-01-24 12:00:00+1459'
    )

    Z3_AdditionalCasUserFields.objects.create(
        user_id=tester10_user.id,
        kayttajatyyppi='VIRKAILIJA',
        henkilo_oid='1.2.345680002',
        asiointikieli_koodi='fi',
        last_modified='2019-01-24 12:00:00+1459'
    )

    Z3_AdditionalCasUserFields.objects.create(
        user_id=pk_vakajarjestaja_1_user.id,
        kayttajatyyppi='PALVELU',
        henkilo_oid='',
        asiointikieli_koodi='fi',
        last_modified='2019-01-24 12:00:00+1459'
    )

    Z3_AdditionalCasUserFields.objects.create(
        user_id=pk_vakajarjestaja_2_user.id,
        kayttajatyyppi='PALVELU',
        henkilo_oid='',
        asiointikieli_koodi='fi',
        last_modified='2019-01-24 12:00:00+1459'
    )

    Z4_CasKayttoOikeudet.objects.create(
        user_id=tester2_user.id,
        organisaatio_oid='1.2.246.562.10.34683023489',
        kayttooikeus='VARDA-TALLENTAJA',
        last_modified='2019-01-24 12:00:00+1459'
    )


def create_koodisto(name, name_koodistopalvelu, codes):
    import datetime

    from django.db import IntegrityError

    from varda.models import Z2_Koodisto, Z2_Code, Z2_CodeTranslation
    from varda import koodistopalvelu

    update_datetime = datetime.datetime.strptime('2020-05-14', '%Y-%m-%d')
    update_datetime = update_datetime.replace(tzinfo=datetime.timezone.utc)

    try:
        koodisto_obj = Z2_Koodisto.objects.create(name=name,
                                                  name_koodistopalvelu=name_koodistopalvelu,
                                                  update_datetime=update_datetime,
                                                  version=1)
        for code in codes:
            code_obj = Z2_Code.objects.create(koodisto=koodisto_obj, code_value=code)
            for lang in koodistopalvelu.LANGUAGE_CODES:
                Z2_CodeTranslation.objects.create(code=code_obj, language=lang, name='test nimi',
                                                  description='test kuvaus', short_name='test lyhyt nimi')
    except IntegrityError:
        logger.warning(f'Error creating koodisto {name}')


def create_initial_koodisto_data():
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

    for key, value in koodistopalvelu.KOODISTOPALVELU_DICT.items():
        # Some koodistot have been added afterwards, they have their own create functions
        if key.value not in koodisto_codes:
            continue
        create_koodisto(key.value, value, koodisto_codes[key.value])


def create_postinumero_koodisto_data():
    from varda import koodistopalvelu

    # No need to load all postinumerot initially because they are not used in validation
    codes = ['00100', '99999']

    koodisto_enum = koodistopalvelu.Koodistot.postinumero_koodit
    name = koodisto_enum.value
    koodistopalvelu_name = koodistopalvelu.KOODISTOPALVELU_DICT.get(koodisto_enum)

    create_koodisto(name, koodistopalvelu_name, codes)


def create_virhe_koodisto_data():
    from varda import koodistopalvelu

    # Load all codes that are used in unit testing
    codes = ['GE001', 'GE002', 'GE003', 'GE004', 'GE005', 'GE006', 'GE007', 'GE008', 'GE009', 'GE010', 'GE011',
             'GE012', 'GE013', 'GE014', 'GE015', 'GE016', 'GE017', 'GE018', 'DY001', 'DY002', 'DY003', 'DY004',
             'DY005', 'DY006', 'DY007', 'VJ001', 'VJ002', 'VJ003', 'VJ004', 'VJ005', 'VJ006', 'VJ007', 'VJ008',
             'VJ009', 'TP001', 'TP002', 'TP003', 'TP004', 'TP005', 'TP006', 'TP007', 'TP008', 'TP009', 'TP010',
             'TP011', 'TP012', 'TP013', 'TP014', 'TP015', 'TP016', 'TO001', 'KP001', 'HE001', 'HE002', 'HE003',
             'HE004', 'HE005', 'HE006', 'HE007', 'HE008', 'HE009', 'HE010', 'HE011', 'HE012', 'HE013', 'LA001',
             'LA002', 'LA003', 'LA004', 'LA005', 'LA006', 'LA007', 'LA008', 'VP001', 'VP002', 'VP003', 'VP004',
             'VP005', 'VP006', 'VP007', 'VP008', 'VP009', 'VP010', 'VP011', 'VS001', 'VS002', 'VS003', 'VS004',
             'VS005', 'VS006', 'VS007', 'VS008', 'VS009', 'VS010', 'VS011', 'VS012', 'VS013', 'MA001', 'MA002',
             'MA003', 'MA004', 'MA005', 'MA006', 'MA007', 'MA008', 'MA009', 'MA010', 'MA011', 'MA012', 'MA013',
             'MA014', 'PT001', 'PT002', 'PT003', 'PT004', 'PT005', 'PT006', 'PT007', 'PT008', 'PT009', 'PT010',
             'PO001', 'PO002', 'PO003', 'TY001', 'TY002', 'TY003', 'TY004', 'TY005', 'TU001', 'TU002', 'TU003',
             'PS001', 'PS002', 'PS003', 'PS004', 'PS005', 'PS006', 'PS007', 'TA001', 'TA002', 'TA003', 'TA004',
             'TA005', 'TA006', 'TA007', 'TA008', 'TA009', 'TA010', 'TA011', 'TA012', 'TA013', 'PP001', 'PP002',
             'PP003', 'PP004', 'PP005', 'PP006', 'PP007', 'PP008', 'TH001', 'TH002', 'TH003', 'TH004', 'TH005',
             'TH006', 'TK001', 'TK002', 'TK003', 'TK004', 'TK005', 'TK006', 'TK007', 'TK008', 'TK009', 'TK010',
             'TK011', 'TK012', 'TK013', 'TK014', 'TK015', 'PE001', 'PE002', 'PE003', 'PE004', 'PE005', 'PE006',
             'PE007', 'PE008', 'AD001', 'AD002', 'AD003', 'AD004', 'AD005', 'LO001', 'LO002', 'RF001', 'RF002',
             'RF003', 'RF004', 'KO001', 'KO002', 'KO003', 'KO004', 'MI001', 'MI002', 'MI003', 'MI004', 'MI005',
             'MI006', 'MI007', 'MI008', 'MI009', 'MI010', 'MI011', 'MI012', 'MI013', 'MI014', 'MI015', 'MI016']

    koodisto_enum = koodistopalvelu.Koodistot.virhe_koodit
    name = koodisto_enum.value
    koodistopalvelu_name = koodistopalvelu.KOODISTOPALVELU_DICT.get(koodisto_enum)

    create_koodisto(name, koodistopalvelu_name, codes)


def create_yritysmuoto_koodisto_data():
    from varda import koodistopalvelu
    from varda.enums.koodistot import Koodistot
    from varda.models import Z2_CodeTranslation

    # Load all codes that are used in unit testing
    codes = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18',
             '19', '20', '21', '22', '23', '24', '25', '26', '28', '29', '30', '31', '32', '33', '35', '36', '37', '38',
             '39', '40', '41', '42', '43', '44', '45', '46', '47', '48', '49', '50', '51', '52', '53', '54', '55', '56',
             '57', '58', '59', '60', '61', '62', '63', '64', '70', '71', '80', '81', '82', '83', '84', '85', '90', '91']

    koodisto_enum = koodistopalvelu.Koodistot.yritysmuoto_koodit
    name = koodisto_enum.value
    koodistopalvelu_name = koodistopalvelu.KOODISTOPALVELU_DICT.get(koodisto_enum)

    create_koodisto(name, koodistopalvelu_name, codes)

    for code_translation in (('0', 'Ei yritysmuotoa',), ('16', 'Osakeyhtiö',), ('41', 'Kunta',),
                             ('42', 'Kuntayhtymä',),):
        (Z2_CodeTranslation.objects
         .filter(code__code_value=code_translation[0], code__koodisto__name=Koodistot.yritysmuoto_koodit.value,
                 language='FI')
         .update(name=code_translation[1]))


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
    if 'VARDA_ENVIRONMENT_TYPE' in os.environ:
        fetch_huoltajat_task.delay()


def create_or_update_henkilo(henkilo_defaults, henkilo_hetu, henkilo_hetu_hash, henkilo_oid):
    from varda.models import Henkilo

    henkilo = None
    henkilo_created = False
    if henkilo_query := Henkilo.objects.filter(henkilotunnus_unique_hash=henkilo_hetu_hash):
        henkilo_query.update(**henkilo_defaults, henkilo_oid=henkilo_oid)
    elif henkilo_query := Henkilo.objects.filter(henkilo_oid=henkilo_oid):
        henkilo_query.update(**henkilo_defaults, henkilotunnus=henkilo_hetu, henkilotunnus_unique_hash=henkilo_hetu_hash)
    else:
        henkilo = Henkilo.objects.create(
            **henkilo_defaults,
            henkilotunnus=henkilo_hetu,
            henkilotunnus_unique_hash=henkilo_hetu_hash,
            henkilo_oid=henkilo_oid
        )
        henkilo_created = True
    return henkilo_created, henkilo


def create_onr_lapsi_huoltajat(create_all_vakajarjestajat=False):
    """
    https://wiki.eduuni.fi/display/CscVarda/Testihuoltajat
    """
    from django.contrib.auth.models import Group
    from guardian.shortcuts import assign_perm
    from varda.enums.organisaatiotyyppi import Organisaatiotyyppi
    from varda.models import Lapsi
    from varda.organisaatiopalvelu import create_organization_using_oid

    print('Adding lapset + huoltajat (from ONR) in test data.')

    henkilo_1_oid = '1.2.246.562.24.68159811823'
    henkilo_1_hetu = 'gAAAAABeOX1kRyEYLW_6z3YCD3vApCjVNJwR4M-ExlfAKqWLvQJZ__6Ztxqha-S0DmuxjZchXlNN2hVIMisYZLDXXzY2fk1IJQ=='
    henkilo_1_hetu_hash = 'd1206ea57e7fd86f2f7c50fe572936a1b6639128a8ca9941b1c8f66037e0fa83'

    henkilo_2_oid = '1.2.246.562.24.49084901393'
    henkilo_2_hetu = 'gAAAAABeOX14By1klio088ccJeF6-hSRJ7LZdneYM85hdQQzq1D2N7JS1rYTOQk_gwftL1wkMog4sjXlA_RXDPBNGKT1gUvNDw=='
    henkilo_2_hetu_hash = 'd9becaf41cd69a312f39a9bb1d0974257423a84b2b6b8d95d7c51922ad6a8bbc'

    henkilo_3_oid = '1.2.246.562.24.65027773627'
    henkilo_3_hetu = 'gAAAAABeOX2KpfzGhI-8NHJeD6y5GN-2AW-rBNljGHN-dATt4vnhuwXANY8lS3yk2OKb7Ap_ChaZxpg4wpQ6OR2MuyoI9yzl-w=='
    henkilo_3_hetu_hash = '05b5dce8a3c078b9861dda10a01290c085473b9764e083935d30ba8baadc09a7'

    henkilo_4_oid = '1.2.246.562.24.86721655046'
    henkilo_4_hetu = 'gAAAAABeOX2cvW10r98xVX8XEcoYQeeSkQrlduGif7O0goMcaN5WBolz625GBHl_JF64lMsm5RAIWEcs7JO3qfGO0VGMwe5BRw=='
    henkilo_4_hetu_hash = '1dad3c4e6e1fc076cd11ecb49f39d88a40678425a129394a51d02709b3168f55'

    henkilo_1_defaults = {
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
        'postitoimipaikka': ''
    }
    henkilo_1_created, henkilo_1 = create_or_update_henkilo(henkilo_1_defaults, henkilo_1_hetu, henkilo_1_hetu_hash, henkilo_1_oid)

    henkilo_2_defaults = {
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
        'postitoimipaikka': ''
    }
    henkilo_2_created, henkilo_2 = create_or_update_henkilo(henkilo_2_defaults, henkilo_2_hetu, henkilo_2_hetu_hash, henkilo_2_oid)

    henkilo_3_defaults = {
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
        'postitoimipaikka': ''
    }
    henkilo_3_created, henkilo_3 = create_or_update_henkilo(henkilo_3_defaults, henkilo_3_hetu, henkilo_3_hetu_hash, henkilo_3_oid)

    henkilo_4_defaults = {
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
        'postitoimipaikka': ''
    }
    henkilo_4_created, henkilo_4 = create_or_update_henkilo(henkilo_4_defaults, henkilo_4_hetu, henkilo_4_hetu_hash, henkilo_4_oid)

    vakajarjestaja_oids = get_vakajarjestaja_oids(create_all_vakajarjestajat)
    for organisaatio_oid in vakajarjestaja_oids:
        create_organization_using_oid(organisaatio_oid, Organisaatiotyyppi.VAKAJARJESTAJA.value)

        group_tallentaja = Group.objects.get(name='VARDA-TALLENTAJA_' + organisaatio_oid)
        group_katselija = Group.objects.get(name='VARDA-KATSELIJA_' + organisaatio_oid)
        group_paakayttaja = Group.objects.get(name='VARDA-PAAKAYTTAJA_' + organisaatio_oid)
        group_huoltajatiedot_tallentaja = Group.objects.get(name='HUOLTAJATIETO_TALLENNUS_' + organisaatio_oid)
        group_huoltajatiedot_katselija = Group.objects.get(name='HUOLTAJATIETO_KATSELU_' + organisaatio_oid)

        vakajarjestaja_permission_groups = [group_tallentaja, group_katselija, group_paakayttaja,
                                            group_huoltajatiedot_tallentaja, group_huoltajatiedot_katselija]

        if henkilo_1_created:
            lapsi_1 = Lapsi.objects.create(henkilo=henkilo_1)
            for permission_group in vakajarjestaja_permission_groups:
                assign_perm('change_lapsi', permission_group, lapsi_1)

        if henkilo_2_created:
            lapsi_2 = Lapsi.objects.create(henkilo=henkilo_2)
            for permission_group in vakajarjestaja_permission_groups:
                assign_perm('view_lapsi', permission_group, lapsi_2)

        if henkilo_3_created:
            lapsi_3 = Lapsi.objects.create(henkilo=henkilo_3)
            for permission_group in vakajarjestaja_permission_groups:
                assign_perm('view_lapsi', permission_group, lapsi_3)

        if henkilo_4_created:
            lapsi_4 = Lapsi.objects.create(henkilo=henkilo_4)
            for permission_group in vakajarjestaja_permission_groups:
                assign_perm('view_lapsi', permission_group, lapsi_4)

    fetch_huoltajat_if_applicable()


def _create_tyontekija_and_related_data(tyontekija, tutkinto_list=(), palvelussuhde_list=()):
    from varda.models import Tyontekija

    resp_tyontekija = _make_post_request('/api/henkilosto/v1/tyontekijat/', tyontekija)
    tyontekija_id = json.loads(resp_tyontekija.content)['id']
    tyontekija_obj = Tyontekija.objects.get(id=tyontekija_id)

    for tutkinto in tutkinto_list:
        tutkinto_dict = {
            'henkilo_oid': tyontekija_obj.henkilo.henkilo_oid,
            'vakajarjestaja_oid': tyontekija_obj.vakajarjestaja.organisaatio_oid,
            'tutkinto_koodi': tutkinto
        }
        _make_post_request('/api/henkilosto/v1/tutkinnot/', tutkinto_dict)

    for palvelussuhde in palvelussuhde_list:
        palvelussuhde_dict = palvelussuhde[0]
        palvelussuhde_dict['tyontekija'] = f'/api/henkilosto/v1/tyontekijat/{tyontekija_id}/'

        tyoskentelypaikka_list = palvelussuhde[1]
        pidempi_poissaolo_list = palvelussuhde[2]

        resp_palvelussuhde = _make_post_request('/api/henkilosto/v1/palvelussuhteet/', palvelussuhde_dict)
        palvelussuhde_id = json.loads(resp_palvelussuhde.content)['id']

        for tyoskentelypaikka in tyoskentelypaikka_list:
            tyoskentelypaikka['palvelussuhde'] = f'/api/henkilosto/v1/palvelussuhteet/{palvelussuhde_id}/'
            _make_post_request('/api/henkilosto/v1/tyoskentelypaikat/', tyoskentelypaikka)

        for pidempi_poissaolo in pidempi_poissaolo_list:
            pidempi_poissaolo['palvelussuhde'] = f'/api/henkilosto/v1/palvelussuhteet/{palvelussuhde_id}/'
            _make_post_request('/api/henkilosto/v1/pidemmatpoissaolot/', pidempi_poissaolo)


def create_henkilosto():
    import datetime
    from varda.models import TilapainenHenkilosto

    _create_tyontekija_and_related_data(
        {
            'henkilo_oid': '1.2.246.562.24.2431884920041',
            'vakajarjestaja_oid': '1.2.246.562.10.34683023489',
            'lahdejarjestelma': 1,
            'tunniste': 'testing-tyontekija1'
        },
        tutkinto_list=('321901', '712104', '613101',),
        palvelussuhde_list=(
            (
                {
                    'tyosuhde_koodi': 1,
                    'tyoaika_koodi': 1,
                    'tutkinto_koodi': '321901',
                    'tyoaika_viikossa': '38.73',
                    'alkamis_pvm': '2020-03-01',
                    'paattymis_pvm': '2030-03-01',
                    'lahdejarjestelma': '1',
                    'tunniste': 'testing-palvelussuhde1'
                },
                (
                    {
                        'toimipaikka_oid': '1.2.246.562.10.9395737548815',
                        'alkamis_pvm': '2020-03-01',
                        'paattymis_pvm': '2020-09-10',
                        'tehtavanimike_koodi': '39407',
                        'kelpoisuus_kytkin': False,
                        'kiertava_tyontekija_kytkin': False,
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-tyoskentelypaikka1'
                    },
                    {
                        'toimipaikka_oid': '1.2.246.562.10.9395737548815',
                        'alkamis_pvm': '2020-03-01',
                        'paattymis_pvm': '2020-10-02',
                        'tehtavanimike_koodi': '39407',
                        'kelpoisuus_kytkin': False,
                        'kiertava_tyontekija_kytkin': False,
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-tyoskentelypaikka1-1'
                    },
                    {
                        'toimipaikka_oid': '1.2.246.562.10.9395737548815',
                        'alkamis_pvm': '2020-03-01',
                        'paattymis_pvm': '2021-05-02',
                        'tehtavanimike_koodi': '64212',
                        'kelpoisuus_kytkin': False,
                        'kiertava_tyontekija_kytkin': False,
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-tyoskentelypaikka2'
                    },
                ),
                (),
            ),
        )
    )
    _create_tyontekija_and_related_data(
        {
            'henkilo_oid': '1.2.246.562.24.2431884920042',
            'vakajarjestaja_oid': '1.2.246.562.10.34683023489',
            'lahdejarjestelma': 1,
            'tunniste': 'testing-tyontekija2'
        },
        tutkinto_list=('321901', '712104', '613101',),
        palvelussuhde_list=(
            (
                {
                    'tyosuhde_koodi': 1,
                    'tyoaika_koodi': 1,
                    'tutkinto_koodi': '321901',
                    'tyoaika_viikossa': '20.00',
                    'alkamis_pvm': '2020-03-01',
                    'paattymis_pvm': '2030-03-01',
                    'lahdejarjestelma': 1,
                    'tunniste': 'testing-palvelussuhde2'
                },
                (
                    {
                        'toimipaikka_oid': '1.2.246.562.10.9395737548815',
                        'alkamis_pvm': '2020-03-01',
                        'paattymis_pvm': '2030-03-01',
                        'tehtavanimike_koodi': '77826',
                        'kelpoisuus_kytkin': False,
                        'kiertava_tyontekija_kytkin': False,
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-tyoskentelypaikka2_1'
                    },
                ),
                (),
            ),
            (
                {
                    'tyosuhde_koodi': 1,
                    'tyoaika_koodi': 1,
                    'tutkinto_koodi': '712104',
                    'tyoaika_viikossa': '5.0',
                    'alkamis_pvm': '2020-03-01',
                    'paattymis_pvm': '2030-03-01',
                    'lahdejarjestelma': 1,
                    'tunniste': 'testing-palvelussuhde2-2'
                },
                (),
                (
                    {
                        'alkamis_pvm': '2024-01-01',
                        'paattymis_pvm': '2025-01-01',
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-pidempipoissaolo1'
                    },
                ),
            ),
        )
    )
    _create_tyontekija_and_related_data(
        {
            'henkilo_oid': '1.2.246.562.24.2431884920043',
            'vakajarjestaja_oid': '1.2.246.562.10.34683023489',
            'lahdejarjestelma': 1,
            'tunniste': 'testing-tyontekija3'
        },
        tutkinto_list=('321901', '712104', '613101',)
    )
    _create_tyontekija_and_related_data(
        {
            'henkilo_oid': '1.2.246.562.24.2431884920044',
            'vakajarjestaja_oid': '1.2.246.562.10.34683023489',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-tyontekija4'
        },
        tutkinto_list=('321901', '712104', '613101',),
        palvelussuhde_list=(
            (
                {
                    'tyosuhde_koodi': '1',
                    'tyoaika_koodi': '1',
                    'tutkinto_koodi': '613101',
                    'tyoaika_viikossa': '20.00',
                    'alkamis_pvm': '2020-03-01',
                    'paattymis_pvm': '2030-03-01',
                    'lahdejarjestelma': '1',
                    'tunniste': 'testing-palvelussuhde4'
                },
                (
                    {
                        'toimipaikka_oid': '1.2.246.562.10.9395737548815',
                        'alkamis_pvm': '2020-03-01',
                        'paattymis_pvm': '2020-10-02',
                        'tehtavanimike_koodi': '77826',
                        'kelpoisuus_kytkin': True,
                        'kiertava_tyontekija_kytkin': False,
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-tyoskentelypaikka4'
                    },
                ),
                (),
            ),
        )
    )
    _create_tyontekija_and_related_data(
        {
            'henkilo_oid': '1.2.246.562.24.2431884920041',
            'vakajarjestaja_oid': '1.2.246.562.10.93957375488',
            'lahdejarjestelma': 1,
            'tunniste': 'testing-tyontekija5'
        },
        tutkinto_list=('321901',),
        palvelussuhde_list=(
            (
                {
                    'tyosuhde_koodi': 1,
                    'tyoaika_koodi': 1,
                    'tutkinto_koodi': '321901',
                    'tyoaika_viikossa': '20.00',
                    'alkamis_pvm': '2020-09-01',
                    'paattymis_pvm': '2030-03-01',
                    'lahdejarjestelma': 1,
                    'tunniste': 'testing-palvelussuhde5'
                },
                (
                    {
                        'toimipaikka_oid': '1.2.246.562.10.9395737548811',
                        'alkamis_pvm': '2020-09-02',
                        'paattymis_pvm': '2020-10-02',
                        'tehtavanimike_koodi': '77826',
                        'kelpoisuus_kytkin': True,
                        'kiertava_tyontekija_kytkin': False,
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-tyoskentylypaikka5-1'
                    },
                    {
                        'toimipaikka_oid': '1.2.246.562.10.9395737548810',
                        'alkamis_pvm': '2020-09-02',
                        'paattymis_pvm': '2020-10-02',
                        'tehtavanimike_koodi': '43525',
                        'kelpoisuus_kytkin': True,
                        'kiertava_tyontekija_kytkin': False,
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-tyoskentylypaikka5-2'
                    },
                ),
                (),
            ),
        )
    )
    _create_tyontekija_and_related_data(
        {
            'henkilo_oid': '1.2.246.562.24.2431884920045',
            'vakajarjestaja_oid': '1.2.246.562.10.34683023489',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-tyontekija-kiertava'
        },
        tutkinto_list=('321901', '712104', '613101',),
        palvelussuhde_list=(
            (
                {
                    'tyosuhde_koodi': '1',
                    'tyoaika_koodi': '1',
                    'tutkinto_koodi': '321901',
                    'tyoaika_viikossa': '20.00',
                    'alkamis_pvm': '2020-03-01',
                    'paattymis_pvm': '2030-03-01',
                    'lahdejarjestelma': '1',
                    'tunniste': 'testing-palvelussuhde-kiertava'
                },
                (
                    {
                        'toimipaikka_oid': None,
                        'alkamis_pvm': '2020-03-01',
                        'paattymis_pvm': '2020-10-02',
                        'tehtavanimike_koodi': '77826',
                        'kelpoisuus_kytkin': True,
                        'kiertava_tyontekija_kytkin': True,
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-tyoskentylypaikka-kiertava',
                    },
                ),
                (),
            ),
        )
    )
    _create_tyontekija_and_related_data(
        {
            'henkilo_oid': '1.2.246.562.24.4645229637988',
            'vakajarjestaja_oid': '1.2.246.562.10.57294396385',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-tyontekija6'
        },
        tutkinto_list=('321901',),
        palvelussuhde_list=(
            (
                {
                    'tyosuhde_koodi': '1',
                    'tyoaika_koodi': '1',
                    'tutkinto_koodi': '321901',
                    'tyoaika_viikossa': '20.00',
                    'alkamis_pvm': '2021-01-01',
                    'lahdejarjestelma': '1',
                    'tunniste': 'testing-palvelussuhde6'
                },
                (
                    {
                        'toimipaikka_oid': '1.2.246.562.10.6727877596658',
                        'alkamis_pvm': '2021-01-02',
                        'tehtavanimike_koodi': '43525',
                        'kelpoisuus_kytkin': True,
                        'kiertava_tyontekija_kytkin': False,
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-tyoskentylypaikka6-1',
                    },
                    {
                        'toimipaikka_oid': '1.2.246.562.10.2565458382544',
                        'alkamis_pvm': '2021-01-02',
                        'tehtavanimike_koodi': '43525',
                        'kelpoisuus_kytkin': True,
                        'kiertava_tyontekija_kytkin': False,
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-tyoskentylypaikka6-2',
                    },
                ),
                (
                    {
                        'alkamis_pvm': '2024-01-01',
                        'paattymis_pvm': '2025-01-01',
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-pidempipoissaolo2'
                    },
                ),
            ),
        )
    )
    _create_tyontekija_and_related_data(
        {
            'henkilo_oid': '1.2.246.562.24.5826267847674',
            'vakajarjestaja_oid': '1.2.246.562.10.52966755795',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-tyontekija7'
        },
        tutkinto_list=('321901',),
        palvelussuhde_list=(
            (
                {
                    'tyosuhde_koodi': '1',
                    'tyoaika_koodi': '1',
                    'tutkinto_koodi': '321901',
                    'tyoaika_viikossa': '20.00',
                    'alkamis_pvm': '2021-01-01',
                    'lahdejarjestelma': '1',
                    'tunniste': 'testing-palvelussuhde7'
                },
                (
                    {
                        'toimipaikka_oid': '1.2.246.562.10.9625978384762',
                        'alkamis_pvm': '2021-01-02',
                        'tehtavanimike_koodi': '43525',
                        'kelpoisuus_kytkin': True,
                        'kiertava_tyontekija_kytkin': False,
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-tyoskentylypaikka7',
                    },
                ),
                (
                    {
                        'alkamis_pvm': '2024-01-01',
                        'paattymis_pvm': '2025-01-01',
                        'lahdejarjestelma': '1',
                        'tunniste': 'testing-pidempipoissaolo3'
                    },
                ),
            ),
        )
    )

    tilapainen_henkilosto_list = (
        {
            'vakajarjestaja_oid': '1.2.246.562.10.34683023489',
            'kuukausi': '2020-09-01',
            'tuntimaara': '37.50',
            'tyontekijamaara': 5,
            'lahdejarjestelma': '1',
            'tunniste': 'testing-tilapainenhenkilosto1'
        },
        {
            'vakajarjestaja_oid': '1.2.246.562.10.57294396385',
            'kuukausi': '2020-09-01',
            'tuntimaara': '37.50',
            'tyontekijamaara': 5,
            'lahdejarjestelma': '1',
            'tunniste': 'testing-tilapainenhenkilosto2'
        },
        {
            'vakajarjestaja_oid': '1.2.246.562.10.52966755795',
            'kuukausi': '2020-10-01',
            'tuntimaara': '37.50',
            'tyontekijamaara': 5,
            'lahdejarjestelma': '1',
            'tunniste': 'testing-tilapainenhenkilosto3'
        },
    )
    # Because TilapainenHenkilosto can be saved for current or previous period, we need to save with temporary date and
    # then update the intended date
    date_iterator_init = datetime.date.today()
    date_iterator_init = date_iterator_init.replace(day=1)
    date_iterator_dict = {}
    for tilapainen_henkilosto in tilapainen_henkilosto_list:
        vakajarjestaja_oid = tilapainen_henkilosto['vakajarjestaja_oid']
        date_iterator = date_iterator_dict.get(vakajarjestaja_oid, None)
        if not date_iterator:
            date_iterator = date_iterator_init

        original_date = tilapainen_henkilosto['kuukausi']
        tilapainen_henkilosto['kuukausi'] = date_iterator.strftime('%Y-%m-%d')
        resp = _make_post_request('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        tilapainen_henkilosto_obj = TilapainenHenkilosto.objects.get(id=json.loads(resp.content)['id'])
        tilapainen_henkilosto_obj.kuukausi = original_date
        tilapainen_henkilosto_obj.save()

        # Move to first day of previous month
        date_iterator -= datetime.timedelta(days=1)
        date_iterator_dict[vakajarjestaja_oid] = date_iterator.replace(day=1)

    taydennyskoulutus_list = (
        {
            'taydennyskoulutus_tyontekijat': [
                {'lahdejarjestelma': '1', 'tunniste': 'testing-tyontekija1', 'tehtavanimike_koodi': '39407'},
                {'lahdejarjestelma': '1', 'tunniste': 'testing-tyontekija1', 'tehtavanimike_koodi': '64212'},
                {'lahdejarjestelma': '1', 'tunniste': 'testing-tyontekija4', 'tehtavanimike_koodi': '77826'}
            ],
            'nimi': 'Testikoulutus',
            'suoritus_pvm': '2020-09-01',
            'koulutuspaivia': '1.5',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-taydennyskoulutus1'
        },
        {
            'taydennyskoulutus_tyontekijat': [
                {'lahdejarjestelma': '1', 'tunniste': 'testing-tyontekija2', 'tehtavanimike_koodi': '77826'}
            ],
            'nimi': 'Testikoulutus2',
            'suoritus_pvm': '2020-09-01',
            'koulutuspaivia': '1.5',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-taydennyskoulutus2'
        },
        {
            'taydennyskoulutus_tyontekijat': [
                {'lahdejarjestelma': '1', 'tunniste': 'testing-tyontekija6', 'tehtavanimike_koodi': '43525'}
            ],
            'nimi': 'Testikoulutus3',
            'suoritus_pvm': '2020-09-01',
            'koulutuspaivia': '1.5',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-taydennyskoulutus3'
        },
        {
            'taydennyskoulutus_tyontekijat': [
                {'lahdejarjestelma': '1', 'tunniste': 'testing-tyontekija7', 'tehtavanimike_koodi': '43525'}
            ],
            'nimi': 'Testikoulutus4',
            'suoritus_pvm': '2020-09-01',
            'koulutuspaivia': '1.5',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-taydennyskoulutus4'
        },
    )
    for taydennyskoulutus in taydennyskoulutus_list:
        _make_post_request('/api/henkilosto/v1/taydennyskoulutukset/', taydennyskoulutus)


def create_aikaleima():
    from varda.models import Aikaleima
    from varda.enums.aikaleima_avain import AikaleimaAvain

    Aikaleima.objects.create(avain=AikaleimaAvain.HENKILOMUUTOS_LAST_UPDATE)


def create_login_certs():
    from django.contrib.auth.models import User
    from varda.models import LoginCertificate, Organisaatio

    user = User.objects.get(username='kela_luovutuspalvelu')
    kela_organisaatio = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.2013121014482686198719')

    LoginCertificate.objects.update_or_create(organisaatio=kela_organisaatio, api_path='/api/reporting/v1/kela/etuusmaksatus/aloittaneet/', common_name='kela cert', user=user)
    LoginCertificate.objects.update_or_create(organisaatio=kela_organisaatio, api_path='/api/reporting/v1/kela/etuusmaksatus/lopettaneet/', common_name='kela cert', user=user)
    LoginCertificate.objects.update_or_create(organisaatio=kela_organisaatio, api_path='/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/', common_name='kela cert', user=user)
    LoginCertificate.objects.update_or_create(organisaatio=kela_organisaatio, api_path='/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/', common_name='kela cert', user=user)
    LoginCertificate.objects.update_or_create(organisaatio=kela_organisaatio, api_path='/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/', common_name='kela cert', user=user)


def create_test_data():
    import os
    from django.conf import settings
    from varda.models import Z6_RequestLog, Z6_LastRequest

    create_vakajarjestajat()
    create_toimipaikat_and_painotukset()
    create_paos_toiminta()
    create_henkilot()
    create_lapset()
    create_user_data()
    create_henkilosto()
    create_aikaleima()
    create_login_certs()

    # Remove RequestLog instances created during test data creation
    Z6_RequestLog.objects.all().delete()
    Z6_LastRequest.objects.all().delete()

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
    add_test_users()
    create_test_data()
    add_test_user_permissions()


def _make_post_request(url, json_content):
    import json
    from django.conf import settings
    from django.contrib.auth.models import User
    from rest_framework import status
    from rest_framework.test import APIClient
    from varda.unit_tests.test_utils import assert_status_code

    client = APIClient()
    client.force_authenticate(user=User.objects.get(username='credadmin'))

    # If server is running as HTTPS, use secure requests
    if settings.SECURE_SSL_REDIRECT:
        extra = {
            'secure': True
        }
    else:
        extra = {}

    response = client.post(url, json.dumps(json_content), content_type='application/json', **extra)
    assert_status_code(response, status.HTTP_201_CREATED)
    return response
