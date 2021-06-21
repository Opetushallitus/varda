import { VardaVakajarjestaja, VardaVakajarjestajaUi } from '../../utilities/models';

export const vakajarjestajatStub: Array<VardaVakajarjestaja> = [
  {
    url: 'https://localhost:8000/api/v1/vakajarjestajat/13/',
    id: 13,
    nimi: 'Sotkamo',
    y_tunnus: '0214958-9',
    organisaatio_oid: '1.2.246.562.10.67019405222',
    kunta_koodi: '205',
    postinumero: '87100',
    postitoimipaikka: 'KAJAANI',
    alkamis_pvm: '1978-09-11',
    paattymis_pvm: null,
    muutos_pvm: '2018-12-11 11:11:48.290219+00:00',
    sahkopostiosoite: null,
    ip_osoite: null,
    puhelinnumero: ''
  },
  {
    url: 'https://localhost:8000/api/v1/vakajarjestajat/11/',
    id: 11,
    nimi: 'Kajaanin kaupunki',
    y_tunnus: '0214958-9',
    organisaatio_oid: '1.2.246.562.10.67019405611',
    kunta_koodi: '205',
    postinumero: '87100',
    postitoimipaikka: 'KAJAANI',
    alkamis_pvm: '1978-09-11',
    paattymis_pvm: null,
    muutos_pvm: '2018-12-11 11:11:48.290219+00:00',
    sahkopostiosoite: null,
    ip_osoite: null,
    puhelinnumero: ''
  },
  {
    url: 'https://localhost:8000/api/v1/vakajarjestajat/10/',
    id: 11,
    nimi: 'Vakatoimija10',
    y_tunnus: '0214958-9',
    organisaatio_oid: '1.2.246.562.10.67019405633',
    kunta_koodi: '205',
    postinumero: '87100',
    postitoimipaikka: 'KAJAANI',
    alkamis_pvm: '1978-09-11',
    paattymis_pvm: null,
    muutos_pvm: '2018-12-11 11:11:48.290219+00:00',
    sahkopostiosoite: null,
    ip_osoite: null,
    puhelinnumero: ''
  }
];


export const vakajarjestajatUIStub: Array<VardaVakajarjestajaUi> = [
  {
    url: 'https://localhost:8000/api/v1/vakajarjestajat/13/',
    id: 13,
    nimi: 'Sotkamo',
    y_tunnus: '0214958-9',
    organisaatio_oid: '1.2.246.562.10.67019405222',
    kunnallinen_kytkin: true
  },
  {
    url: 'https://localhost:8000/api/v1/vakajarjestajat/11/',
    id: 11,
    nimi: 'Kajaanin kaupunki',
    y_tunnus: '0214958-9',
    organisaatio_oid: '1.2.246.562.10.67019405611',
    kunnallinen_kytkin: true
  },
  {
    url: 'https://localhost:8000/api/v1/vakajarjestajat/10/',
    id: 10,
    nimi: 'Vakatoimija10',
    y_tunnus: '0214958-9',
    organisaatio_oid: '1.2.246.562.10.67019405633',
    kunnallinen_kytkin: false
  },
];
