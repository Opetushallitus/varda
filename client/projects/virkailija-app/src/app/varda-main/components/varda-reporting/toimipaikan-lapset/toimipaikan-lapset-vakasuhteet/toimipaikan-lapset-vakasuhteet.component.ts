import { Component, Input, ViewEncapsulation } from '@angular/core';
import { ToimipaikanLapsiVakasuhde } from '../../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { VardaDateService } from '../../../../services/varda-date.service';
import { VirkailijaTranslations } from '../../../../../../assets/i18n/virkailija-translations.enum';

@Component({
  selector: 'app-toimipaikan-lapset-vakasuhteet',
  templateUrl: './toimipaikan-lapset-vakasuhteet.component.html',
  styleUrls: ['../toimipaikan-lapset.component.css', 'toimipaikan-lapset-vakasuhteet.component.css'],
  encapsulation: ViewEncapsulation.None
})
export class ToimipaikanLapsetVakasuhteetComponent {
  @Input() vakasuhde: ToimipaikanLapsiVakasuhde;

  i18n = VirkailijaTranslations;

  constructor(private dateService: VardaDateService) {}

  getDateRangeDisplayValue(startDate: string, endDate: string): string {
    return this.dateService.getDateRangeDisplayValue(startDate, endDate);
  }
}
