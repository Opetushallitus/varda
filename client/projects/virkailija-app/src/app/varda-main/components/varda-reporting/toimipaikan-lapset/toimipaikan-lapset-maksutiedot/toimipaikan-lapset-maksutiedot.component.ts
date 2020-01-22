import { Component, Input } from '@angular/core';
import {VardaMaksunPerusteKoodistoService} from '../../../../../core/services/varda-maksun-peruste-koodisto.service';
import { TranslateService } from '@ngx-translate/core';
import {ToimipaikanLapsiMaksutieto} from '../../../../../utilities/models/dto/varda-henkilohaku-dto.model';

@Component({
  selector: 'app-toimipaikan-lapset-maksutiedot',
  templateUrl: './toimipaikan-lapset-maksutiedot.component.html',
  styleUrls: ['../toimipaikan-lapset.component.css']
})
export class ToimipaikanLapsetMaksutiedotComponent {

  @Input() maksutieto: ToimipaikanLapsiMaksutieto;

  constructor(private vardaMaksunPerustekoodistoService: VardaMaksunPerusteKoodistoService,
    private translateService: TranslateService) {}

  formatMaksunperusteDisplayValue(koodi: string) {
    const allOptions = this.vardaMaksunPerustekoodistoService.getKoodistoOptions();
    const selectedOption = allOptions.find((_koodi) => _koodi.koodiArvo.toUpperCase() === koodi.toUpperCase());
    if (selectedOption) {
      const metadata = this.vardaMaksunPerustekoodistoService
        .getKoodistoOptionMetadataByLang(selectedOption.metadata, this.translateService.currentLang);

      return metadata.nimi;
    }
    return '-';
  }
}
