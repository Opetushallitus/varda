import { Component, Input } from '@angular/core';

@Component({
    selector: 'app-varda-success-modal',
    templateUrl: './varda-success-modal.component.html',
    styleUrls: ['./varda-success-modal.component.css'],
    standalone: false
})
export class VardaSuccessModalComponent {

  @Input() identifier: string;
  @Input() successTitle: string;
  @Input() successMsg: string;

  constructor() { }
}
