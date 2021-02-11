import { Component, Input, OnInit } from '@angular/core';

@Component({
  selector: 'app-robo-id',
  templateUrl: './robo-id.component.html',
  styleUrls: ['./robo-id.component.css']
})
export class RoboIdComponent implements OnInit {
  @Input() tunniste: number;
  @Input() nimi: string;
  @Input() alkamis_pvm: string;
  @Input() paattymis_pvm: string;
  constructor() { }

  ngOnInit(): void {
  }

}
