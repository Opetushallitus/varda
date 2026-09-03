import { Directive, ElementRef} from '@angular/core';


import { VardaAccessibilityService } from '../../core/services/varda-accessibility.service';

@Directive({
    selector: '[appHighContrast]',
    standalone: false
})
export class HighContrastDirective {
  private elem: HTMLElement;

  constructor(el: ElementRef, private localStorageWrapper: VardaAccessibilityService) {
    this.elem = el.nativeElement;
    this.localStorageWrapper.highContrastIsEnabled().subscribe((isEnabled) => {
      if (isEnabled) {
        this.elem.classList.add('varda-high-contrast');
      } else {
        this.elem.classList.remove('varda-high-contrast');
      }
    });
  }
}
