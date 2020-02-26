import { Component, OnInit, Input, Output, EventEmitter, ViewChildren, QueryList, ContentChildren, forwardRef } from '@angular/core';
import { VardaRadioButtonComponent } from './varda-radio-button/varda-radio-button.component';

enum Breakpoints {
  xs = 'xs',
  sm = 'sm',
  md = 'md',
  lg = 'lg',
  xl = 'xl',
}

export interface RadioButtonResponse {
  event: Event;
  value: any
}


@Component({
  selector: 'app-varda-radio-button-group',
  templateUrl: './varda-radio-button-group.component.html',
  styleUrls: ['./varda-radio-button-group.component.css']
})
export class VardaRadioButtonGroupComponent implements OnInit {
  @Input() name: string;
  @Input() class: string;
  @Input() responsive: Breakpoints;
  @Input() wrap: Breakpoints;
  @Output() change: EventEmitter<RadioButtonResponse> = new EventEmitter(true);
  @ContentChildren(forwardRef(() => VardaRadioButtonComponent), { descendants: true }) radioButtons: QueryList<VardaRadioButtonComponent>;
  classes: string[];


  constructor() { }

  ngOnInit() {
    this.classes = [
      this.class,
      this.wrap ? `wrap-${this.wrap}` : null,
      this.responsive ? `responsive-${this.responsive}` : null,
    ].filter(c => c)
  }

  ngAfterContentInit() {
    this.radioButtons.forEach(radio => {
      radio.name = this.name;
      radio.onChange = this.change;
    });
  }
}
