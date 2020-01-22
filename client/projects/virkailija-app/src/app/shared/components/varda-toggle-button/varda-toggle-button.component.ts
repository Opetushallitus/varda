import {Component, Input, OnInit} from '@angular/core';

@Component({
  selector: 'app-varda-toggle-button',
  templateUrl: './varda-toggle-button.component.html',
  styleUrls: ['./varda-toggle-button.component.css']
})
export class VardaToggleButtonComponent implements OnInit {
  // Is show or hide button displayed
  @Input() isUp: boolean;
  @Input() showTextKey: string;
  @Input() hideTextKey: string;

  constructor() { }

  ngOnInit() {
  }

}
