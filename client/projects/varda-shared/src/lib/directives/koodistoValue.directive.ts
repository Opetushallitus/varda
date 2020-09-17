import { Directive, ElementRef, Input, AfterContentInit } from '@angular/core';
import { VardaKoodistoService } from '../koodisto.service';
import { KoodistoEnum } from '../dto/koodisto-models';

export type CodeFormat = 'short' | 'long';

@Directive({
  selector: '[libKoodistoValue]'
})
export class KoodistoValueDirective implements AfterContentInit {
  private koodistoType: KoodistoEnum;
  @Input()
  set libKoodistoValue(value: KoodistoEnum) {
    this.koodistoType = value;
  }
  @Input() format: CodeFormat = 'short';
  private elem: HTMLInputElement;

  constructor(
    private el: ElementRef,
    private koodistoService: VardaKoodistoService
  ) {
    this.elem = el.nativeElement;
  }

  ngAfterContentInit() {
    if (this.elem.textContent) {
      const codeValue = this.elem.textContent.trim();
      this.koodistoService.getCodeValueFromKoodisto(this.koodistoType, codeValue).subscribe({
        next: code => {
          let result = '';

          if (!code) {
            result = codeValue;
          } else if (this.format === 'long') {
            result = `${code.name} (${codeValue})`;
          } else {
            result = code.name;
          }

          this.elem.textContent = result;
        },
        error: err => console.error(err)
      });
    }
  }
}
