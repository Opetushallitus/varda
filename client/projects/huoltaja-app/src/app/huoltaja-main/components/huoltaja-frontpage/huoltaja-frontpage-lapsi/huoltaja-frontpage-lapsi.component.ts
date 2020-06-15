import { Component, Input } from '@angular/core';
import { HenkiloDTO } from 'projects/huoltaja-app/src/app/utilities/models/dto/henkilo-dto';
import { HuoltajaTranslations } from 'projects/huoltaja-app/src/assets/i18n/translations.enum';

@Component({
  selector: 'app-huoltaja-frontpage-lapsi',
  templateUrl: './huoltaja-frontpage-lapsi.component.html',
  styleUrls: ['../huoltaja-frontpage.component.css', './huoltaja-frontpage-lapsi.component.css']
})
export class HuoltajaFrontpageLapsiComponent {

  @Input() lapsiDto: HenkiloDTO;
  translation = HuoltajaTranslations;

  toggleLapsi(lapsiDto: HenkiloDTO) {
    lapsiDto.toggle_expanded = !lapsiDto.toggle_expanded;
  }

}
