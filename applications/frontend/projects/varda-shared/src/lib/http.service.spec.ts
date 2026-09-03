import { TestBed } from '@angular/core/testing';

import { HttpService } from './http.service';
import {HttpClient} from '@angular/common/http';

describe('HttpService', () => {
  let httpService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        HttpService,
        {provide: HttpClient, useValue: {}}
      ]
    });
    httpService = TestBed.inject<HttpService>(HttpService);
  });

  it('should be created', () => {
    const service: HttpService = TestBed.inject<HttpService>(HttpService);
    expect(service).toBeTruthy();
  });

  it('Should return base64 encoded string ', () => {
    const base64EncodedStr = httpService.base64encode('aaa');
    expect(base64EncodedStr).toEqual('YWFh');
  });

});
