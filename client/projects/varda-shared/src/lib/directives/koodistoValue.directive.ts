import { Directive, ElementRef, Input, AfterContentInit, OnChanges, SimpleChanges } from '@angular/core';
import { VardaKoodistoService } from '../koodisto.service';
import { KoodistoEnum } from '../models/koodisto-models';
import { VardaDateService } from '../varda-date.service';
import { CommonTranslations } from '../../common-translations.enum';
import { HelperService } from '../helper.service';

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
  private i18n = CommonTranslations;
  private disabledSinceString = '';

  constructor(
    private el: ElementRef,
    private koodistoService: VardaKoodistoService,
    private dateService: VardaDateService,
    private helperService: HelperService
  ) {
    this.elem = el.nativeElement;
    this.disabledSinceString = this.helperService.getTranslation(this.i18n.code_disabled_since);
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
          let suffix = '';
          if (!code.active) {
            suffix = `, ${this.disabledSinceString} ${this.dateService.apiDateToUiDate(code.paattymis_pvm)}`;
          }
          result = `${code.name} (${codeValue}${suffix})`;
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
