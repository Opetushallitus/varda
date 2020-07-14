import { Directive, ElementRef, Input, AfterContentInit } from '@angular/core';
import { VardaKoodistoService } from '../koodisto.service';
import { KoodistoEnum } from '../dto/koodisto-models';


@Directive({
  selector: '[libKoodistoValue]'
})
export class KoodistoValueDirective implements AfterContentInit {
  private koodistoType: KoodistoEnum;
  @Input()
  set libKoodistoValue(value: KoodistoEnum) {
    this.koodistoType = value;
  }

  private elem: HTMLInputElement;

  constructor(
    private el: ElementRef,
    private koodistoService: VardaKoodistoService
  ) {
    this.elem = el.nativeElement;
  }

  ngAfterContentInit() {
    if (this.elem.textContent) {
      this.koodistoService.getCodeValueFromKoodisto(this.koodistoType, this.elem.textContent.trim()).subscribe({
        next: code => this.elem.textContent = code?.name || this.elem.textContent,
        error: err => console.error(err)
      });
    }
  }
}
