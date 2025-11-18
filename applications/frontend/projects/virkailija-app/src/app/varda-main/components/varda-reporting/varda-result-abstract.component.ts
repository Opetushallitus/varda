import { Component } from '@angular/core';
import { VirkailijaTranslations } from '../../../../assets/i18n/virkailija-translations.enum';
import { VardaDateService } from 'varda-shared';

interface NumberOfDisplayed {
  kielipainotus?: number;
  toiminnallinenpainotus?: number;
  vakapaatos?: number;
  maksutieto?: number;
  palvelussuhde?: number;
  taydennyskoulutus?: number;
}

@Component({
  template: ''
})
export abstract class VardaResultAbstractComponent {
  i18n = VirkailijaTranslations;

  numberOfDisplayed: NumberOfDisplayed = {kielipainotus: 0, toiminnallinenpainotus: 0, vakapaatos: 0, maksutieto: 0,
    palvelussuhde: 0, taydennyskoulutus: 0};

  protected constructor(private dateService: VardaDateService) { }

  getDateRangeDisplayValue(startDate: string, endDate: string): string {
    return this.dateService.getDateRangeDisplayValue(startDate, endDate);
  }

  getDateDisplayValue(dateString: string): string {
    return this.dateService.getDateDisplayValue(dateString);
  }

  getBooleanLabel(booleanValue: boolean): string {
    return booleanValue ? this.i18n.yes : this.i18n.no;
  }
}
