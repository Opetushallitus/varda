import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-robo-id',
  templateUrl: './robo-id.component.html',
  styleUrls: ['./robo-id.component.css']
})
export class RoboIdComponent {
  @Input() tunniste: number;
  @Input() nimi: string;
  @Input() alkamis_pvm: string;
  @Input() paattymis_pvm: string;
  constructor() { }
}
