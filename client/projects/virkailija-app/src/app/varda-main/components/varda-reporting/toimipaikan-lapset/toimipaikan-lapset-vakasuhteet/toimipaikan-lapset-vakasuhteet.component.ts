import { Component, Input } from '@angular/core';
import {ToimipaikanLapsiVakasuhde} from '../../../../../utilities/models/dto/varda-henkilohaku-dto.model';

@Component({
  selector: 'app-toimipaikan-lapset-vakasuhteet',
  templateUrl: './toimipaikan-lapset-vakasuhteet.component.html',
  styleUrls: ['../toimipaikan-lapset.component.css']
})
export class ToimipaikanLapsetVakasuhteetComponent {

  @Input() vakasuhde: ToimipaikanLapsiVakasuhde;
}
