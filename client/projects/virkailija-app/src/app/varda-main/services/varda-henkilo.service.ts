import {Injectable} from '@angular/core';
import {VardaEntityNames, VardaExtendedHenkiloModel, VardaHenkiloDTO, VardaHenkiloSearchConfiguration} from '../../utilities/models';

@Injectable()
export class VardaHenkiloService {

  constructor() { }

  createHenkiloSearchObj(activeFilter: string, searchValue: string) {
    const henkiloSearchObj = new VardaHenkiloSearchConfiguration();
    henkiloSearchObj.searchValue = searchValue;
    henkiloSearchObj.displayLapset = activeFilter === VardaEntityNames.LAPSI ? true : false;
    henkiloSearchObj.displayTyontekijat = activeFilter === VardaEntityNames.TYONTEKIJA ? true : false;
    henkiloSearchObj.displayAll = activeFilter === 'kaikki' ? true : false;
    return henkiloSearchObj;
  }

  getHenkiloCountText(henkiloList: Array<VardaExtendedHenkiloModel>): string {
    const noOfLapsi = henkiloList.filter((item) => item.lapsi !== undefined);
    const noOfTyontekija = henkiloList.filter((item) => item.tyontekija !== undefined);
    return `${noOfLapsi.length} Lasta, ${noOfTyontekija.length} Työntekijää`;
  }

  henkiloIsLapsi(henkilo: VardaHenkiloDTO): boolean {
    return henkilo && henkilo.lapsi.length > 0;
  }

  searchByStrAndEntityFilter(searchObj: VardaHenkiloSearchConfiguration,
    henkiloList: Array<VardaExtendedHenkiloModel>): Array<VardaExtendedHenkiloModel> {
    const searchValue = searchObj.searchValue;
    const henkilot = henkiloList.filter((item) => {
      const henkilo = item.henkilo;
      if (searchObj.displayLapset && henkilo.lapsi.length === 0) {
        return false;
      }

      if (searchObj.displayTyontekijat && henkilo.tyontekija.length === 0) {
        return false;
      }

      const toCompareValue = henkilo.sukunimi + ' ' + henkilo.etunimet;
      return (toCompareValue.toLowerCase().indexOf(searchValue.toLowerCase()) > -1);
    });
    henkilot.sort(this.sortByLastName);

    return henkilot;
  }

  sortByLastName(a: any, b: any): number {
    const henkiloA = a.henkilo;
    const henkiloB = b.henkilo;

    if (henkiloA.sukunimi < henkiloB.sukunimi) {
      return -1;
    }
    if (henkiloA.sukunimi > henkiloB.sukunimi) {
      return 1;
    }
    return 0;
  }

}
