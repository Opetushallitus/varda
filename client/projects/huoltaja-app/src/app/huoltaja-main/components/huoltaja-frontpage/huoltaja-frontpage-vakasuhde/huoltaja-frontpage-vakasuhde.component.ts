import { Component, Input } from '@angular/core';

import { VarhaiskasvatussuhdeDTO, VarhaiskasvatuspaatosDTO } from '../../../../utilities/models/dto/huoltaja-frontpage-dto';

@Component({
  selector: 'app-huoltaja-frontpage-vakasuhde',
  templateUrl: './huoltaja-frontpage-vakasuhde.component.html',
  styleUrls: ['../huoltaja-frontpage.component.css']
})
export class HuoltajaFrontpageVakasuhdeComponent {

  @Input() vakasuhde: VarhaiskasvatussuhdeDTO;

  toggleVakapaatos(vakapaatosDto: VarhaiskasvatuspaatosDTO) {
    vakapaatosDto.toggle_expanded = !vakapaatosDto.toggle_expanded;
  }
}
