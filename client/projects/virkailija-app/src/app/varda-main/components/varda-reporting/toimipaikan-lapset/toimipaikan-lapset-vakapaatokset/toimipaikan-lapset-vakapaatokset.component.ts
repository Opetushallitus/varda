import { Component, Input, OnInit } from '@angular/core';
import { VardaApiWrapperService } from '../../../../../core/services/varda-api-wrapper.service';
import { VardaFieldSet } from '../../../../../utilities/models';
import { VardaFormService } from '../../../../../core/services/varda-form.service';
import { TranslateService } from '@ngx-translate/core';
import { ToimipaikanLapsiVakapaatos } from '../../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { KoodistoEnum } from 'varda-shared';
import { VirkailijaTranslations } from '../../../../../../assets/i18n/virkailija-translations.enum';
import { VardaDateService } from '../../../../services/varda-date.service';

@Component({
  selector: 'app-toimipaikan-lapset-vakapaatokset',
  templateUrl: './toimipaikan-lapset-vakapaatokset.component.html',
  styleUrls: ['../toimipaikan-lapset.component.css']
})
export class ToimipaikanLapsetVakapaatoksetComponent implements OnInit {
  @Input() vakapaatos: ToimipaikanLapsiVakapaatos;

  i18n = VirkailijaTranslations;
  koodistoEnum = KoodistoEnum;
  varhaiskasvatuspaatoksetFieldSets: Array<VardaFieldSet> = [];

  constructor(
    private vardaFormService: VardaFormService,
    private translateService: TranslateService,
    private vardaApiWrapperService: VardaApiWrapperService,
    private dateService: VardaDateService
  ) {}

  ngOnInit() {
    this.vardaApiWrapperService.getVarhaiskasvatuspaatosFieldSets().subscribe((data) => {
      this.varhaiskasvatuspaatoksetFieldSets = data['fieldsets'];
    });
  }

  getDateRangeDisplayValue(startDate: string, endDate: string): string {
    return this.dateService.getDateRangeDisplayValue(startDate, endDate);
  }
}
