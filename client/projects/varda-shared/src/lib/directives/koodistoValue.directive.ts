import { Directive, ElementRef, Input, AfterContentInit, OnChanges, SimpleChanges } from '@angular/core';
import { VardaKoodistoService } from '../koodisto.service';
import { KoodistoEnum } from '../models/koodisto-models';

export type CodeFormat = 'short' | 'long';

@Directive({
  selector: '[libKoodistoValue]'
})
export class KoodistoValueDirective implements AfterContentInit, OnChanges {
  @Input() value: string;
  @Input() format: CodeFormat = 'short';

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

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.value) {
      this.updateTextContent(this.value);
    }
  }
}
