import { VardaToimipaikkaMinimalDto } from '../../utilities/models/dto/varda-toimipaikka-dto.model';
import { Hallinnointijarjestelma } from '../../utilities/models/enums/hallinnointijarjestelma';

export const toimipaikatMinStub: Array<VardaToimipaikkaMinimalDto> = [
  {
    'hallinnointijarjestelma': Hallinnointijarjestelma.VARDA,
    'paos_toimipaikka_kytkin': false,
    'url': 'https://varda-manual-testing-370.rahtiapp.fi/api/v1/toimipaikat/1/',
    'organisaatio_oid': 'toimipaikka_0001',
    'nimi': 'Espoo',
    'nimi_original': 'Espoo'
  },
  {
    'hallinnointijarjestelma': Hallinnointijarjestelma.VARDA,
    'paos_toimipaikka_kytkin': false,
    'url': 'https://varda-manual-testing-370.rahtiapp.fi/api/v1/toimipaikat/4/',
    'nimi': 'Toimipaikka5',
    'nimi_original': 'toimipaikka_0004',
    'organisaatio_oid': '123123'
  },
  {
    'hallinnointijarjestelma': Hallinnointijarjestelma.VARDA,
    'paos_toimipaikka_kytkin': false,
    'url': 'https://varda-manual-testing-370.rahtiapp.fi/api/v1/toimipaikat/5/',
    'nimi': 'Kivelän päiväkoti',
    'nimi_original': 'Kivelän päiväkoti',
    'organisaatio_oid': 'toimipaikka_0005'
  },
  {
    'hallinnointijarjestelma': Hallinnointijarjestelma.VARDA,
    'paos_toimipaikka_kytkin': false,
    'url': 'https://varda-manual-testing-370.rahtiapp.fi/api/v1/toimipaikat/6/',
    'nimi': '1111aggdgf554saf',
    'nimi_original': '1111aggdgf554saf',
    'organisaatio_oid': 'toimipaikka_0006'
  }
];
