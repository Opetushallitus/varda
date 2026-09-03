import {
  Component,
  Input,
  Output,
  EventEmitter,
  ChangeDetectorRef,
  ChangeDetectionStrategy
} from '@angular/core';

@Component({
    selector: 'app-varda-radio-button',
    templateUrl: './varda-radio-button.component.html',
    styleUrls: ['./varda-radio-button.component.css'],
    changeDetection: ChangeDetectionStrategy.OnPush,
    standalone: false
})
export class VardaRadioButtonComponent {
  @Input() id: string;
  @Input() value: any;
  @Input() class?: string;
  @Input() disabled?: boolean;
  @Input() tabIndex?: number;
  @Input() name?: string;
  @Input() required?: boolean;
  @Input() ariaDescribedby?: string;
  @Input() ariaLabel?: string;
  @Input() ariaLabelledby?: string;
  @Output() valueChange = new EventEmitter(true);
  private _checked?: boolean;

  constructor(private _changeDetector: ChangeDetectorRef) { }

  @Input()
  get checked() {
    return this._checked;
  }
  set checked(value) {
    this._checked = value;
    this._changeDetector.markForCheck();
  }

  _onClick(event: Event) {
    event.stopPropagation();
  }

  _onChange(event: Event) {
    event.stopPropagation();
    this.checked = true;
    this.valueChange.emit({ event, value: this.value });
  }
}
