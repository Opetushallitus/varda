import { Component, OnInit, Input, Output, EventEmitter } from '@angular/core';

@Component({
  selector: 'app-varda-radio-button',
  templateUrl: './varda-radio-button.component.html',
  styleUrls: ['./varda-radio-button.component.css']
})
export class VardaRadioButtonComponent implements OnInit {
  @Input() id: string;
  @Input() value: any;
  @Input() class?: string;
  @Input() checked?: boolean;
  @Input() disabled?: boolean;
  @Input() tabIndex?: number;
  @Input() name?: string;
  @Input() required?: boolean;
  @Input() ariaDescribedby?: string;
  @Input() ariaLabel?: string;
  @Input() ariaLabelledby?: string;
  @Output() onChange = new EventEmitter(true);

  constructor() { }

  ngOnInit() {
  }

  _onChange(event) {
    this.onChange.emit({ event: event, value: event.target.value });
  }
}
