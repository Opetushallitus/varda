import { Injectable } from '@angular/core';
import { VardaFieldSet } from '../../utilities/models';
import { environment } from '../../../environments/environment';
import { sha256 } from 'js-sha256';

@Injectable()
export class VardaUtilityService {

  constructor() { }

  deepcopyArray(fieldSetsSource: Array<VardaFieldSet>): Array<VardaFieldSet> {
    return JSON.parse(JSON.stringify(fieldSetsSource));
  }

  parseIdFromUrl(url: string): string {
    const urlParts = url.split('/');
    return urlParts[urlParts.length - 2];
  }

  splitHostname(hostname: string): string {
    const hostnameParts = hostname.split('.');
    const domain = hostnameParts[1];
    return domain;
  }

  getVirkailijaRaamitUrl(locationHostname: string): string {
    const domain = this.splitHostname(locationHostname);
    if (domain === 'opintopolku') {
      return `${environment.virkailijaOpintopolkuUrl}${environment.virkailijaRaamitScriptPath}`;
    } else if (domain === 'testiopintopolku' || locationHostname === 'localhost') {
      return `${environment.virkailijaTestiOpintopolkuUrl}${environment.virkailijaRaamitScriptPath}`;
    }

    return null;
  }

  getOpintopolkuUrl(locationHostname: string): string {
    const hostname = locationHostname;
    const domain = this.splitHostname(hostname);
    if (domain === 'opintopolku') {
      return `${environment.virkailijaOpintopolkuUrl}`;
    } else if (domain === 'testiopintopolku') {
      return `${environment.virkailijaTestiOpintopolkuUrl}`;
    } else {
      return null;
    }
  }

  parseSearchParams(url: string, searchParams: Object): string {
    if (searchParams['search']) {
      searchParams['search'] = this.hashHetu(searchParams['search']);
    }

    url += '?';
    url += Object.keys(searchParams)
      .filter(key => searchParams[key] !== null && searchParams[key] !== undefined)
      .map(key => `${key}=${searchParams[key]}`)
      .join('&');

    return url;
  }

  hashHetu(rawHetu: string) {
    const hetu_regex = /^\d{6}[A+\-]\d{3}[0-9A-FHJ-NPR-Y]$/;
    if (rawHetu && hetu_regex.test(rawHetu)) {
      return sha256.create().update(rawHetu).hex();
    }
    return rawHetu;
  }

}
