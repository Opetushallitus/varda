import { Directive, ElementRef, Input, AfterContentInit, OnChanges, SimpleChanges } from '@angular/core';
import { VardaKoodistoService } from '../koodisto.service';
import { KoodistoEnum } from '../models/koodisto-models';

@Directive({
  selector: '[libKoodistoValue]'
})
export class KoodistoValueDirective implements AfterContentInit, OnChanges {
  @Input() value: string;
  @Input() format: 'short' | 'long' = 'short';

  private koodistoType: KoodistoEnum;
  private elem: HTMLInputElement;

  constructor(private el: ElementRef, private koodistoService: VardaKoodistoService) {
    this.elem = el.nativeElement;
  }

  @Input()
  set libKoodistoValue(value: KoodistoEnum) {
    this.koodistoType = value;
  }

  ngAfterContentInit() {
    if (!this.value) {
      this.updateTextContent(this.elem.textContent.trim());
    }
  }

  updateTextContent(codeValue: string) {
    if (!codeValue) {
      this.elem.textContent = '';
      return;
    }

    this.koodistoService.getCodeValueFromKoodisto(this.koodistoType, codeValue).subscribe({
      next: code => {
        this.elem.textContent = code ? this.koodistoService.getCodeFormattedValue(this.format, code) : codeValue;
      },
      error: err => console.error(err)
    });
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.value) {
      this.updateTextContent(this.value);
    }
  }
}
