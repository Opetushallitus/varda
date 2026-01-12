import {
  AfterViewInit,
  Component,
  ContentChild,
  ElementRef,
  ViewEncapsulation
} from '@angular/core';
import { MatSelect } from '@angular/material/select';

@Component({
    selector: 'app-varda-select',
    templateUrl: './varda-select.component.html',
    styleUrls: ['./varda-select.component.css'],
    encapsulation: ViewEncapsulation.None,
    standalone: false
})
export class VardaSelectComponent implements AfterViewInit {
  @ContentChild(MatSelect) matSelect!: MatSelect;
  @ContentChild(MatSelect, {read: ElementRef}) matSelectElement: ElementRef;

  constructor() { }

  ngAfterViewInit() {
    this.matSelectElement.nativeElement.addEventListener('keydown', (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        if (this.matSelect.panelOpen) {
          event.stopPropagation();
          this.matSelect.close();
        }
      }
    });
  }
}
