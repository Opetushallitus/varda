import { Component, Input } from '@angular/core';

import { LapsiDTO } from '../../../../utilities/models/dto/huoltaja-frontpage-dto';

@Component({
  selector: 'app-huoltaja-frontpage-lapsi',
  templateUrl: './huoltaja-frontpage-lapsi.component.html',
  styleUrls: ['../huoltaja-frontpage.component.css']
})
export class HuoltajaFrontpageLapsiComponent {

  @Input() lapsiDto: LapsiDTO;

  toggleLapsi(lapsiDto: LapsiDTO) {
    lapsiDto.toggle_expanded = !lapsiDto.toggle_expanded;
  }
}
