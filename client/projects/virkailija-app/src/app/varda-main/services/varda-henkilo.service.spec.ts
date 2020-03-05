import { TestBed, inject } from '@angular/core/testing';

import { VardaHenkiloService } from './varda-henkilo.service';
import { henkiloList } from '../../shared/testmocks/henkilo';

describe('VardaHenkiloService', () => {

  let vardaHenkiloService: VardaHenkiloService;
  const henkilot = henkiloList;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [VardaHenkiloService]
    });

    vardaHenkiloService = TestBed.get(VardaHenkiloService);
  });

  it('Should create henkiloSearchConfiguration object by search value and active filter', () => {
    const searchObj1 = vardaHenkiloService.createHenkiloSearchObj('kaikki', 'aaa');
    expect(searchObj1.displayAll).toBeTruthy();
    expect(searchObj1.displayLapset).toBeFalsy();
    expect(searchObj1.displayTyontekijat).toBeFalsy();
    expect(searchObj1.searchValue).toEqual('aaa');

    const searchObj2 = vardaHenkiloService.createHenkiloSearchObj('lapsi', 'bbb');
    expect(searchObj2.displayAll).toBeFalsy();
    expect(searchObj2.displayLapset).toBeTruthy();
    expect(searchObj2.displayTyontekijat).toBeFalsy();
    expect(searchObj2.searchValue).toEqual('bbb');

    const searchObj3 = vardaHenkiloService.createHenkiloSearchObj('tyontekija', 'ccc');
    expect(searchObj3.displayAll).toBeFalsy();
    expect(searchObj3.displayLapset).toBeFalsy();
    expect(searchObj3.displayTyontekijat).toBeTruthy();
    expect(searchObj3.searchValue).toEqual('ccc');
  });

  it('Should return henkilolist by search value and active filter', () => {
    const henkilot1 = vardaHenkiloService.searchByStrAndEntityFilter(
      {
        displayAll: false,
        displayLapset: true,
        displayTyontekijat: false,
        searchValue: 'Virtanen'
      }, henkilot);

    expect(henkilot1.length).toEqual(1);

    const henkilot2 = vardaHenkiloService.searchByStrAndEntityFilter(
      {
        displayAll: false,
        displayLapset: false,
        displayTyontekijat: true,
        searchValue: 'Virtanen'
      }, henkilot);

    expect(henkilot2.length).toEqual(0);

    const henkilot3 = vardaHenkiloService.searchByStrAndEntityFilter(
      {
        displayAll: true,
        displayLapset: false,
        displayTyontekijat: false,
        searchValue: 'Virtanen'
      }, henkilot);

      expect(henkilot3.length).toEqual(1);

    const henkilot4 = vardaHenkiloService.searchByStrAndEntityFilter(
      {
        displayAll: true,
        displayLapset: false,
        displayTyontekijat: false,
        searchValue: ''
      }, henkilot);

      expect(henkilot4.length).toEqual(henkilot.length);
  });

  it('Should return sorted henkilo list', () => {
    const sortedHenkilot = vardaHenkiloService.searchByStrAndEntityFilter(
      {
        displayAll: true,
        displayLapset: false,
        displayTyontekijat: false,
        searchValue: ''
      }, henkilot);

      expect(sortedHenkilot.length).toEqual(henkilot.length);
      expect(sortedHenkilot[0].henkilo.sukunimi).toEqual('Aaltonen');
      expect(sortedHenkilot[1].henkilo.sukunimi).toEqual('Meikäläinen');
      expect(sortedHenkilot[2].henkilo.sukunimi).toEqual('Saarinen');
      expect(sortedHenkilot[3].henkilo.sukunimi).toEqual('Virtanen');
  });

  it('Should return henkilo list summary text correctly according to lapsi and tyontekija count', () => {
    const summaryText = vardaHenkiloService.getHenkiloCountText(henkilot);
    expect(summaryText).toBe('2 Lasta, 0 Työntekijää');
  });
});
