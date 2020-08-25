import { TestBed } from '@angular/core/testing';
import { VardaApiWrapperService } from './varda-api-wrapper.service';
import { VardaVakajarjestajaService } from './varda-vakajarjestaja.service';
import { VardaDateService } from '../../varda-main/services/varda-date.service';
import { VardaUtilityService } from '../../core/services/varda-utility.service';
import { fieldsets } from '../../shared/testmocks/fieldsets';
import {
    VardaToimipaikkaDTO,
    VardaVarhaiskasvatussuhdeDTO,
    VardaVakajarjestaja } from '../../utilities/models';
import { VardaApiService } from './varda-api.service';
import {HttpTestingController} from '@angular/common/http/testing';
import {HttpBackend} from '@angular/common/http';
import {HttpClient, HttpHandler} from '@angular/common/http';
import * as moment from 'moment';

describe('VardaApiWrapperService', () => {

  let vardaApiWrapperService: VardaApiWrapperService;
  let vardaApiService: any;
  let vardaVakajarjestajaService: VardaVakajarjestajaService;

  const toimipaikkaFieldSets = fieldsets.toimipaikat;
  const varhaiskasvatuspaatosFieldSets = fieldsets.varhaiskasvatuspaatokset;

  let createHenkiloByHenkiloDetailsSpy, createVarhaiskasvatussuhdeSpy,
  getHenkiloBySsnOrHenkiloOidSpy, getHenkilotSpy,
  getVakaJarjestajaByIdSpy, getAllVakajarjestajaForLoggedInUser,
  getToimipaikkaByIdSpy, getToimipaikatForVakajarjestajaSpy,
  getAllVarhaiskasvatussuhteetByToimipaikkaSpy,
  getKielipainotuksetByToimipaikkaSpy, getVarhaiskasvatussuhteetByLapsiSpy,
  getVarhaiskasvatuspaatoksetByLapsiSpy,
  deleteKielipainotusSpy, deleteToimintapainotusSpy, deleteVarhaiskasvatuspaatosSpy,
  deleteVarhaiskasvatussuhdeSpy, patchVakajarjestajaSpy, getToimipaikanLapsetSpy,
  getSelectedVakajarjestajaIdSpy;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        VardaApiWrapperService,
        VardaApiService,
        VardaVakajarjestajaService,
        VardaDateService,
        VardaUtilityService,
        {provide: HttpBackend, useClass: HttpTestingController},
        HttpClient,
        HttpHandler
      ]
    });
    vardaApiWrapperService = TestBed.inject<VardaApiWrapperService>(VardaApiWrapperService);
    vardaApiService = TestBed.inject<VardaApiService>(VardaApiService);
    vardaVakajarjestajaService = TestBed.inject<VardaVakajarjestajaService>(VardaVakajarjestajaService);

    createHenkiloByHenkiloDetailsSpy = spyOn(vardaApiService, 'createHenkilo').and.returnValue({});
    createVarhaiskasvatussuhdeSpy = spyOn(vardaApiService, 'createVarhaiskasvatussuhde').and.returnValue({});
    getHenkiloBySsnOrHenkiloOidSpy = spyOn(vardaApiService, 'getHenkiloBySsnOrHenkiloOid').and.returnValue({});
    getHenkilotSpy = spyOn(vardaApiService, 'getHenkilot').and.returnValue({});
    getVakaJarjestajaByIdSpy = spyOn(vardaApiService, 'getVakaJarjestajaById').and.returnValue({});
    getAllVakajarjestajaForLoggedInUser = spyOn(vardaApiService, 'getAllVakajarjestajaForLoggedInUser').and.returnValue({});
    deleteKielipainotusSpy = spyOn(vardaApiService, 'deleteKielipainotus').and.returnValue({});
    deleteToimintapainotusSpy = spyOn(vardaApiService, 'deleteToimintapainotus').and.returnValue({});
    deleteVarhaiskasvatuspaatosSpy = spyOn(vardaApiService, 'deleteVarhaiskasvatuspaatos').and.returnValue({});
    deleteVarhaiskasvatussuhdeSpy = spyOn(vardaApiService, 'deleteVarhaiskasvatussuhde').and.returnValue({});
    getToimipaikkaByIdSpy = spyOn(vardaApiService, 'getToimipaikkaById').and.returnValue({});
    getToimipaikatForVakajarjestajaSpy = spyOn(vardaApiService, 'getToimipaikatForVakaJarjestaja').and.returnValue({});
    getAllVarhaiskasvatussuhteetByToimipaikkaSpy = spyOn(vardaApiService, 'getAllVarhaiskasvatussuhteetByToimipaikka').and.returnValue({});
    getKielipainotuksetByToimipaikkaSpy = spyOn(vardaApiService, 'getKielipainotuksetByToimipaikka').and.returnValue({});
    getVarhaiskasvatussuhteetByLapsiSpy = spyOn(vardaApiService, 'getVarhaiskasvatussuhteetByLapsi').and.returnValue({});
    getVarhaiskasvatuspaatoksetByLapsiSpy = spyOn(vardaApiService, 'getVarhaiskasvatuspaatoksetByLapsi').and.returnValue({});
    patchVakajarjestajaSpy = spyOn(vardaApiService, 'patchVakajarjestaja').and.returnValue({});
    getToimipaikanLapsetSpy = spyOn(vardaApiService, 'getLapsetForToimipaikat').and.returnValue({});
    getSelectedVakajarjestajaIdSpy = spyOn(vardaVakajarjestajaService, 'getSelectedVakajarjestajaId').and.returnValue('1');
  });

  it('Should call createHenkilo with ssn', () => {
    const ssn = '120456-123C';
    const firstnames = 'Matti Erik';
    const nickname = 'Matti';
    const lastname = 'Meikäläinen';
    const isSsn = true;
    const result = vardaApiWrapperService.createHenkiloByHenkiloDetails(ssn, firstnames, nickname, lastname, isSsn);
    expect(createHenkiloByHenkiloDetailsSpy).toHaveBeenCalledWith({
      etunimet: 'Matti Erik',
      kutsumanimi: 'Matti',
      sukunimi: 'Meikäläinen',
      henkilotunnus: '120456-123C'});
  });

  it('Should call getHenkiloBySsnOrHenkiloOid with ssn or oid', () => {
    const ssn = '120456-123C';
    const oid = '1.2.246.562.24.65335265652';
    const result1 = vardaApiWrapperService.getHenkiloBySsnOrHenkiloOid(ssn, true);
    expect(getHenkiloBySsnOrHenkiloOidSpy).toHaveBeenCalledWith({henkilotunnus: '120456-123C'});

    const result2 = vardaApiWrapperService.getHenkiloBySsnOrHenkiloOid(oid, false);
    expect(getHenkiloBySsnOrHenkiloOidSpy).toHaveBeenCalledWith({henkilo_oid: '1.2.246.562.24.65335265652'});
  });

  it('Should call getHenkilot', () => {
    const result = vardaApiWrapperService.getHenkilot();
    expect(getHenkilotSpy).toHaveBeenCalled();
  });

  it('Should pass get request to varda-api.service', () => {
    const id = 'bbadsd';
    const vakatoimijaFormData = new VardaVakajarjestaja();
    vakatoimijaFormData.puhelinnumero = '+3583210931';
    vakatoimijaFormData.sahkopostiosoite = 'frontti@end.com';
    vakatoimijaFormData.tilinumero = 'FI92 2046 1800 0628 04';
    vardaApiWrapperService.getVakaJarjestajaById(id);
    vardaApiWrapperService.getToimipaikkaById(id);
    vardaApiWrapperService.getKielipainotuksetByToimipaikka(id);
    vardaApiWrapperService.getVarhaiskasvatussuhteetByLapsi(id);
    vardaApiWrapperService.getVarhaiskasvatuspaatoksetByLapsi(id);
    vardaApiWrapperService.getToimipaikatForVakajarjestaja(id, null, null);
    vardaApiWrapperService.getVakajarjestajaForLoggedInUser();
    vardaApiWrapperService.saveVakatoimijaData(vakatoimijaFormData);

    expect(getVakaJarjestajaByIdSpy).toHaveBeenCalledWith(id);
    expect(getToimipaikkaByIdSpy).toHaveBeenCalledWith(id);
    expect(getKielipainotuksetByToimipaikkaSpy).toHaveBeenCalledWith(id);
    expect(getVarhaiskasvatussuhteetByLapsiSpy).toHaveBeenCalledWith(id);
    expect(getVarhaiskasvatuspaatoksetByLapsiSpy).toHaveBeenCalledWith(id);
    expect(getToimipaikatForVakajarjestajaSpy).toHaveBeenCalledWith(id, null, null);
    expect(getAllVakajarjestajaForLoggedInUser).toHaveBeenCalled();
    expect(patchVakajarjestajaSpy).toHaveBeenCalledWith('1', vakatoimijaFormData);
  });

  it('Should pass delete request to varda-api.service', () => {
    const id = '7';

    vardaApiWrapperService.deleteKielipainotus(id);
    vardaApiWrapperService.deleteToimintapainotus(id);
    vardaApiWrapperService.deleteVarhaiskasvatuspaatos(id);
    vardaApiWrapperService.deleteVarhaiskasvatussuhde(id);

    expect(deleteKielipainotusSpy).toHaveBeenCalledWith(id);
    expect(deleteToimintapainotusSpy).toHaveBeenCalledWith(id);
    expect(deleteVarhaiskasvatuspaatosSpy).toHaveBeenCalledWith(id);
    expect(deleteVarhaiskasvatussuhdeSpy).toHaveBeenCalledWith(id);
  });

  it('Should create varhaiskasvatussuhdeDTO and call vardaApiService with it', () => {
    const varhaiskasvatuspaatosData = {
        url: 'https://varda-manual-testing-341.rahtiapp.fi/api/v1/varhaiskasvatuspaatokset/1/',
        lapsi: 'https://varda-manual-testing-341.rahtiapp.fi/api/v1/lapset/1/'
    };
    const toimipaikkaData = {
        url: 'https://varda-manual-testing-341.rahtiapp.fi/api/v1/toimipaikat/1/',
        nimi: 'asdf'
    };
    const data = {
        formData: {
            fieldset: {
                alkamis_pvm: moment('2009-07-15', VardaDateService.vardaApiDateFormat)
            }
        },
        fieldSets: [
            {
                id: 'varhaiskasvatussuhde_perustiedot',
                title: 'perustiedot',
                fields: [
                    {
                        key: 'alkamis_pvm',
                        widget: 'date'
                    }
                ]
            }
        ]
    };
    const result = vardaApiWrapperService.createVarhaiskasvatussuhde(toimipaikkaData, varhaiskasvatuspaatosData, data);
    const expectedVarhaiskasvatussuhdeDTO = new VardaVarhaiskasvatussuhdeDTO();
    expectedVarhaiskasvatussuhdeDTO.varhaiskasvatuspaatos =
    'https://varda-manual-testing-341.rahtiapp.fi/api/v1/varhaiskasvatuspaatokset/1/';
    expectedVarhaiskasvatussuhdeDTO.toimipaikka = 'https://varda-manual-testing-341.rahtiapp.fi/api/v1/toimipaikat/1/';
    expectedVarhaiskasvatussuhdeDTO.alkamis_pvm = '2009-07-15';
    expect(createVarhaiskasvatussuhdeSpy).toHaveBeenCalledWith(expectedVarhaiskasvatussuhdeDTO);
  });

  it('Should create VardaToimipaikkaDTO correctly', () => {
    const data = {
      1: {nimi: 'asdf', organisaatio_oid: 'nnnn'},
      2: {vakajarjestaja: 'vaka', paattymis_pvm: moment('2018-02-05', VardaDateService.vardaApiDateFormat)}
    };
    const toimipaikkaDTO = vardaApiWrapperService
      .createDTOwithData<VardaToimipaikkaDTO>(data, new VardaToimipaikkaDTO(), toimipaikkaFieldSets);
    expect(toimipaikkaDTO.nimi).toEqual('asdf');
    expect(toimipaikkaDTO.organisaatio_oid).toEqual('nnnn');
    expect(toimipaikkaDTO.paattymis_pvm).toEqual('2018-02-05');
  });

  it('Should get string-widget value for DTO correctly', () => {
    const stringValue = vardaApiWrapperService.getValueForDto('nimi', 'aaa', toimipaikkaFieldSets);
    expect(stringValue).toEqual('aaa');
  });

  it('Should get select-widget value for DTO correctly', () => {
    const selectValue1 = vardaApiWrapperService.getValueForDto('toimintamuoto_koodi', 'tm03', toimipaikkaFieldSets);
    const selectValue2 = vardaApiWrapperService.getValueForDto('jarjestamismuoto_koodi', 'jm02', varhaiskasvatuspaatosFieldSets);

    expect(selectValue1).toEqual('tm03');
    expect(selectValue2).toEqual('jm02');
  });

  it('Should get selectArr-widget value for DTO correctly', () => {
    const selectValue1 = vardaApiWrapperService.getValueForDto('asiointikieli_koodi', {selectArr: ['FI', 'HR']}, toimipaikkaFieldSets);
    const selectValue2 = vardaApiWrapperService.getValueForDto('asiointikieli_koodi', {selectArr: []}, toimipaikkaFieldSets);

    expect(selectValue1).toEqual(['FI', 'HR']);
    expect(selectValue2).toEqual([]);
  });

  it('Should get checkbox-widget value for DTO correctly', () => {
    const checkboxValue1 = vardaApiWrapperService.getValueForDto('kokopaivainen_vaka_kytkin', true, varhaiskasvatuspaatosFieldSets);
    const checkboxValue2 = vardaApiWrapperService.getValueForDto('paivittainen_vaka_kytkin', false, varhaiskasvatuspaatosFieldSets);
    const checkboxValue3 = vardaApiWrapperService.getValueForDto('paivittainen_vaka_kytkin', '', varhaiskasvatuspaatosFieldSets);
    expect(checkboxValue1).toEqual(true);
    expect(checkboxValue2).toEqual(false);
    expect(checkboxValue3).toEqual(false);
  });

  it('Should get chkgroup-widget value for DTO correctly', () => {
    const chkgroupValue1 = vardaApiWrapperService.getValueForDto('jarjestamismuoto_koodi',
    {jm01: false, jm02: false, jm03: false, jm04: true},
    toimipaikkaFieldSets);

    const chkgroupValue2 = vardaApiWrapperService.getValueForDto('jarjestamismuoto_koodi',
    {jm01: false, jm02: true, jm03: false, jm04: true},
    toimipaikkaFieldSets);

    expect(chkgroupValue1).toEqual(['jm04']);
    expect(chkgroupValue2).toEqual(['jm02', 'jm04']);
  });

  it('Should get date-widget value for DTO correctly', () => {
    const dateValue1 = vardaApiWrapperService.getValueForDto('hakemus_pvm',
      moment('2017-08-26,', VardaDateService.vardaApiDateFormat), varhaiskasvatuspaatosFieldSets);

    const dateValue2 = vardaApiWrapperService.getValueForDto('alkamis_pvm',
      moment('2018-09-01', VardaDateService.vardaApiDateFormat), varhaiskasvatuspaatosFieldSets);

    expect(dateValue1).toEqual('2017-08-26');
    expect(dateValue2).toEqual('2018-09-01');
  });

  it('Should get booleanradio-widget value for DTO correctly', () => {
    const booleanRadioValue1 = vardaApiWrapperService.getValueForDto('vuorohoito_kytkin', '', varhaiskasvatuspaatosFieldSets);
    const booleanRadioValue2 = vardaApiWrapperService.getValueForDto('vuorohoito_kytkin', true, varhaiskasvatuspaatosFieldSets);
    const booleanRadioValue3 = vardaApiWrapperService.getValueForDto('vuorohoito_kytkin', false, varhaiskasvatuspaatosFieldSets);

    expect(booleanRadioValue1).toEqual(false);
    expect(booleanRadioValue2).toEqual(true);
    expect(booleanRadioValue3).toEqual(false);
  });

  it('Should call getLapsetForToimipaikat with vakajarjestajaId and name parameters', () => {
    const vakajarjestajaId = '1';
    const searchParams = {sukunimi: 'Virtanen', etunimet: 'pekka', toimipaikat: '1'};
    const result1 = vardaApiWrapperService.getLapsetForToimipaikat(searchParams, null);
    expect(getToimipaikanLapsetSpy).toHaveBeenCalledWith(vakajarjestajaId, searchParams, null);
  });
});
