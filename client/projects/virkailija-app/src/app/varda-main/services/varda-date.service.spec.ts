import { TestBed, inject } from '@angular/core/testing';
import { VardaDateService } from './varda-date.service';
import * as moment from 'moment';

describe('VardaDateService', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [VardaDateService]
    });
  });

  it('Should convert Moment object to vardaApiDate-style date YYYY-MM-DD', inject([VardaDateService],
    (service: VardaDateService) => {
    const vardaApiDate = service.momentToVardaDate(moment('2009-07-15', VardaDateService.vardaApiDateFormat));
    expect(vardaApiDate.length).toEqual(10);
    expect(vardaApiDate).toEqual('2009-07-15');
  }));

  it('Should convert vardaApiDate-style date YYYY-MM-DD to Moment object', inject([VardaDateService],
    (service: VardaDateService) => {
    const vardaApiDate = service.momentToVardaDate(moment('2009-07-15', VardaDateService.vardaApiDateFormat));
    expect(vardaApiDate.length).toEqual(10);
    expect(vardaApiDate).toEqual('2009-07-15');

    const vardaApiDateStr = '2009-07-15';
    const datepickerDateObj = service.vardaDateToMoment(vardaApiDateStr);

    expect(datepickerDateObj.year()).toEqual(2009);
    expect(datepickerDateObj.month() + 1).toEqual(7);
    expect(datepickerDateObj.date()).toEqual(15);
  }));

  it('Should convert vardaApiDate-style date YYYY-MM-DD to MM.DD.YYYY-style string', inject([VardaDateService],
    (service: VardaDateService) => {
    const vardaApiDateStr1 = '2009-07-15';
    const vardaApiDateStr2 = '2028-02-28';

    const dateStr1 = service.vardaDateToUIStrDate(vardaApiDateStr1);
    const dateStr2 = service.vardaDateToUIStrDate(vardaApiDateStr2);

    expect(dateStr1).toBe('15.07.2009');
    expect(dateStr2).toEqual('28.02.2028');
  }));
});
