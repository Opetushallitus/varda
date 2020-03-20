import { Component, Input } from '@angular/core';
import { HenkiloDTO } from 'projects/huoltaja-app/src/app/utilities/models/dto/henkilo-dto';

@Component({
  selector: 'app-huoltaja-frontpage-lapsi',
  templateUrl: './huoltaja-frontpage-lapsi.component.html',
  styleUrls: ['../huoltaja-frontpage.component.css']
})
export class HuoltajaFrontpageLapsiComponent {

  @Input() lapsiDto: HenkiloDTO;

  toggleLapsi(lapsiDto: HenkiloDTO) {
    lapsiDto.toggle_expanded = !lapsiDto.toggle_expanded;
  }
}
