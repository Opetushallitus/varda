import { Directive, ElementRef, HostListener, OnInit, Input, OnChanges, AfterContentInit } from '@angular/core';
import { NgControl, Validators } from '@angular/forms';
import { TranslateService } from '@ngx-translate/core';
import { LoadingHttpService } from 'varda-shared';
import { HuoltajaApiService } from '../services/huoltaja-api.service';
import { KoodistoDto } from '../utilities/models/dto/koodisto-dto';
import { element } from 'protractor';

export enum KoodistoType {
  kunta = 'kunta',
  kieli = 'kieli',
  sukupuoli = 'sukupuoli',
}

@Directive({
  selector: '[appKoodistoValue]'
})
export class KoodistoValueDirective implements AfterContentInit {
  private koodistoType: KoodistoType;
  @Input()
  set appKoodistoValue(value: KoodistoType) {
    this.koodistoType = value;
  }

  private elem: HTMLInputElement;

  constructor(private el: ElementRef,
    private apiService: HuoltajaApiService,
    private translateService: TranslateService) {
    this.elem = el.nativeElement;
  }

  ngAfterContentInit() {
    if (this.elem.textContent) {
      if (this.koodistoType === KoodistoType.kunta) {
        this.apiService.getKuntakoodistoOptions().subscribe(kuntakoodisto => this.getValueFromKoodisto(kuntakoodisto, this.elem.textContent));
      } else if (this.koodistoType === KoodistoType.kieli) {
        this.apiService.getKielikoodistoOptions().subscribe(kielikoodisto => this.getValueFromKoodisto(kielikoodisto, this.elem.textContent));
      } else if (this.koodistoType === KoodistoType.sukupuoli) {
        this.apiService.getSukupuolikoodistoOptions().subscribe(sukupuolikoodisto => this.getValueFromKoodisto(sukupuolikoodisto, this.elem.textContent));
      }
    }
  }

  getValueFromKoodisto(koodisto: Array<KoodistoDto>, value: string) {
    const lang = this.translateService.currentLang.toLocaleUpperCase();
    const koodiArvo = koodisto.find(koodi => koodi.koodiArvo === value.toLocaleUpperCase());
    if (koodiArvo) {
      const languageValue = koodiArvo.metadata.find(metadata => metadata.kieli.toLocaleUpperCase() === lang);
      this.elem.textContent = languageValue.nimi;
    }
  }
}
