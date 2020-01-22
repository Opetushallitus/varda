import {Injectable} from '@angular/core';
import {VardaFieldSet} from '../../utilities/models';
import {environment} from '../../../environments/environment';

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
    let rv;
    const hostname = locationHostname;
    const domain = this.splitHostname(hostname);
    if (domain === 'opintopolku') {
      rv = `${environment.virkailijaOpintopolkuUrl}${environment.virkailijaRaamitScriptPath}`;
    } else if (domain === 'testiopintopolku') {
      rv = `${environment.virkailijaTestiOpintopolkuUrl}${environment.virkailijaRaamitScriptPath}`;
    } else {
      rv = null;
    }
    return rv;
  }

  getOpintopolkuUrl(locationHostname: string): string {
    let rv;
    const hostname = locationHostname;
    const domain = this.splitHostname(hostname);
    if (domain === 'opintopolku') {
      rv = `${environment.virkailijaOpintopolkuUrl}`;
    } else if (domain === 'testiopintopolku') {
      rv = `${environment.virkailijaTestiOpintopolkuUrl}`;
    } else {
      rv = null;
    }
    return rv;
  }

}
