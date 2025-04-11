import { VardaToimipaikkaDTO } from '../../utilities/models';
import {Hallinnointijarjestelma} from '../../utilities/models/enums/hallinnointijarjestelma';

export const toimipaikatStub: Array<VardaToimipaikkaDTO> = [
    {
      hallinnointijarjestelma: Hallinnointijarjestelma.VARDA,
      paos_toimipaikka_kytkin: false,
      url: 'https://varda-manual-testing-370.rahtiapp.fi/api/v1/toimipaikat/1/',
      vakajarjestaja: 'https://varda-manual-testing-370.rahtiapp.fi/api/v1/vakajarjestajat/2/',
      nimi: 'Espoo',
      organisaatio_oid: 'toimipaikka_0001',
      katuosoite: 'Keilaranta 14',
      postitoimipaikka: 'Espoo',
      postinumero: '02100',
      kunta_koodi: '091',
      puhelinnumero: '+358451112233',
      sahkopostiosoite: 'test1@espoo.fi',
      kasvatusopillinen_jarjestelma_koodi: 'kj98',
      toimintamuoto_koodi: 'tm03',
      toimintakieli_koodi: ['SE', 'FI', 'HR', 'PT', 'IS'],
      jarjestamismuoto_koodi: [],
      varhaiskasvatuspaikat: 120,
      kielipainotus_kytkin: true,
      alkamis_pvm: '2017-02-03',
      paattymis_pvm: null
    },
    {
      hallinnointijarjestelma: Hallinnointijarjestelma.VARDA,
      paos_toimipaikka_kytkin: false,
      url: 'https://varda-manual-testing-370.rahtiapp.fi/api/v1/toimipaikat/4/',
      vakajarjestaja: 'https://varda-manual-testing-370.rahtiapp.fi/api/v1/vakajarjestajat/2/',
      nimi: 'Toimipaikka5',
      organisaatio_oid: 'toimipaikka_0004',
      katuosoite: 'asdfasasdfasdf',
      postitoimipaikka: 'asdfasdfhas',
      postinumero: '20900',
      kunta_koodi: '123',
      puhelinnumero: '+358451112233',
      sahkopostiosoite: 'sddfasdfas@asdf.com',
      kasvatusopillinen_jarjestelma_koodi: 'kj01',
      toimintamuoto_koodi: 'tm01',
      toimintakieli_koodi: ['EN'],
      jarjestamismuoto_koodi: [],
      varhaiskasvatuspaikat: 2,
      kielipainotus_kytkin: false,
      alkamis_pvm: '2018-05-17',
      paattymis_pvm: '2023-05-21'
    },
    {
      hallinnointijarjestelma: Hallinnointijarjestelma.VARDA,
      paos_toimipaikka_kytkin: false,
      url: 'https://varda-manual-testing-370.rahtiapp.fi/api/v1/toimipaikat/5/',
      vakajarjestaja: 'https://varda-manual-testing-370.rahtiapp.fi/api/v1/vakajarjestajat/2/',
      nimi: 'Kivelän päiväkoti',
      organisaatio_oid: 'toimipaikka_0005',
      katuosoite: 'Kiveläntie 2',
      postitoimipaikka: 'Espoo',
      postinumero: '00150',
      kunta_koodi: '023',
      puhelinnumero: '+358451112233',
      sahkopostiosoite: 'kivela@espoo.fi',
      kasvatusopillinen_jarjestelma_koodi: 'kj01',
      toimintamuoto_koodi: 'tm03',
      toimintakieli_koodi: [],
      jarjestamismuoto_koodi: [],
      varhaiskasvatuspaikat: 50,
      kielipainotus_kytkin: true,
      alkamis_pvm: '2011-05-02',
      paattymis_pvm: null
    },
    {
      hallinnointijarjestelma: Hallinnointijarjestelma.VARDA,
      paos_toimipaikka_kytkin: false,
      url: 'https://varda-manual-testing-370.rahtiapp.fi/api/v1/toimipaikat/6/',
      vakajarjestaja: 'https://varda-manual-testing-370.rahtiapp.fi/api/v1/vakajarjestajat/2/',
      nimi: '1111aggdgf554saf',
      organisaatio_oid: 'toimipaikka_0006',
      katuosoite: 'asdfas11111',
      postitoimipaikka: 'asdfasdfg',
      postinumero: '20900',
      kunta_koodi: '20000',
      puhelinnumero: '+358451112233',
      sahkopostiosoite: 'asdfsadfasdf@asdfsdf.com',
      kasvatusopillinen_jarjestelma_koodi: 'kj03',
      toimintamuoto_koodi: 'tm02',
      toimintakieli_koodi: ['FI'],
      jarjestamismuoto_koodi: [],
      varhaiskasvatuspaikat: 2,
      kielipainotus_kytkin: true,
      alkamis_pvm: '2018-05-23',
      paattymis_pvm: null
    }
  ];
