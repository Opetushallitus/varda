import { Component, Input, OnInit } from '@angular/core';
import { VardaApiWrapperService } from '../../../../../core/services/varda-api-wrapper.service';
import { VardaFieldSet } from '../../../../../utilities/models';
import { VardaFormService } from '../../../../../core/services/varda-form.service';
import { TranslateService } from '@ngx-translate/core';
import { ToimipaikanLapsiVakapaatos } from '../../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { KoodistoEnum } from 'varda-shared';

@Component({
  selector: 'app-toimipaikan-lapset-vakapaatokset',
  templateUrl: './toimipaikan-lapset-vakapaatokset.component.html',
  styleUrls: ['../toimipaikan-lapset.component.css']
})
export class ToimipaikanLapsetVakapaatoksetComponent implements OnInit {
  @Input() vakapaatos: ToimipaikanLapsiVakapaatos;

  koodistoEnum = KoodistoEnum;
  varhaiskasvatuspaatoksetFieldSets: Array<VardaFieldSet> = [];

  constructor(
    private vardaFormService: VardaFormService,
    private translateService: TranslateService,
    private vardaApiWrapperService: VardaApiWrapperService
  ) {}

  ngOnInit() {
    this.vardaApiWrapperService.getVarhaiskasvatuspaatosFieldSets().subscribe((data) => {
      this.varhaiskasvatuspaatoksetFieldSets = data['fieldsets'];
    });
  }
}
