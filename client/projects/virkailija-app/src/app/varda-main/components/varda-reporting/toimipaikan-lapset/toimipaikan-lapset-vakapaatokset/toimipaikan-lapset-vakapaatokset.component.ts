import { Component, Input, OnInit } from '@angular/core';
import {VardaApiWrapperService} from '../../../../../core/services/varda-api-wrapper.service';
import {VardaFieldSet} from '../../../../../utilities/models';
import {VardaFormService} from '../../../../../core/services/varda-form.service';
import {TranslateService} from '@ngx-translate/core';
import {ToimipaikanLapsiVakapaatos} from '../../../../../utilities/models/dto/varda-henkilohaku-dto.model';

@Component({
  selector: 'app-toimipaikan-lapset-vakapaatokset',
  templateUrl: './toimipaikan-lapset-vakapaatokset.component.html',
  styleUrls: ['../toimipaikan-lapset.component.css']
})
export class ToimipaikanLapsetVakapaatoksetComponent implements OnInit {

  varhaiskasvatuspaatoksetFieldSets: Array<VardaFieldSet> = [];
  @Input() vakapaatos: ToimipaikanLapsiVakapaatos;

  constructor(private vardaFormService: VardaFormService,
    private translateService: TranslateService,
    private vardaApiWrapperService: VardaApiWrapperService) {}

  formatJarjestamismuotoDisplayValue(jarjestamismuoto_koodi: any) {
    let rv = jarjestamismuoto_koodi;
    const field = this.vardaFormService.findVardaFieldFromFieldSetsByFieldKey('jarjestamismuoto_koodi',
    this.varhaiskasvatuspaatoksetFieldSets);
    if (field) {
      const selectedOption = field.options.find((opt) => opt.code === rv);
      rv = this.getOptionDisplayName(selectedOption);
    }
    return rv ? rv : '-';
  }

  getOptionDisplayName(option: any): string {
    try {
      let rv = '';
      const lang = this.translateService.currentLang.toUpperCase();
      const prop = (lang === 'SV') ? 'displayNameSv' : 'displayNameFi';

      if (option.displayName && option.displayName[prop]) {
        rv = option.displayName[prop];
      }
      return rv;
    } catch (e) {
      return '-';
    }
  }

  ngOnInit() {
    this.vardaApiWrapperService.getVarhaiskasvatuspaatosFieldSets().subscribe((data) => {
      this.varhaiskasvatuspaatoksetFieldSets = data['fieldsets'];
    });
  }
}
