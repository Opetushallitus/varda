import { Component, Input } from '@angular/core';
import { ToimipaikanLapsiMaksutieto } from '../../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { KoodistoEnum } from 'varda-shared';
import { VirkailijaTranslations } from '../../../../../../assets/i18n/virkailija-translations.enum';
import { VardaDateService } from '../../../../services/varda-date.service';

@Component({
  selector: 'app-toimipaikan-lapset-maksutiedot',
  templateUrl: './toimipaikan-lapset-maksutiedot.component.html',
  styleUrls: ['../toimipaikan-lapset.component.css', './toimipaikan-lapset-maksutiedot.component.css']
})
export class ToimipaikanLapsetMaksutiedotComponent {
  @Input() maksutieto: ToimipaikanLapsiMaksutieto;
  @Input() isYksityinen: boolean;

  i18n = VirkailijaTranslations;
  koodistoEnum = KoodistoEnum;

  constructor(private dateService: VardaDateService) {}

  getDateRangeDisplayValue(startDate: string, endDate: string): string {
    return this.dateService.getDateRangeDisplayValue(startDate, endDate);
  }
}
