import { Directive, ElementRef} from '@angular/core';


import { VardaLocalstorageWrapperService } from '../../core/services/varda-localstorage-wrapper.service';

@Directive({
  selector: '[appHighContrast]'
})
export class HighContrastDirective {
  private elem: HTMLElement;

  constructor(el: ElementRef, private localStorageWrapper: VardaLocalstorageWrapperService) {
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
