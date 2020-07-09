import { Component, Input, ViewEncapsulation } from '@angular/core';
import { ToimipaikanLapsiVakasuhde } from '../../../../../utilities/models/dto/varda-henkilohaku-dto.model';

@Component({
  selector: 'app-toimipaikan-lapset-vakasuhteet',
  templateUrl: './toimipaikan-lapset-vakasuhteet.component.html',
  styleUrls: ['../toimipaikan-lapset.component.css', 'toimipaikan-lapset-vakasuhteet.component.css'],
  encapsulation: ViewEncapsulation.None
})
export class ToimipaikanLapsetVakasuhteetComponent {

  @Input() vakasuhde: ToimipaikanLapsiVakasuhde;
}
