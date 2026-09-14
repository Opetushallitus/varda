import { Directive, ElementRef, AfterContentInit } from '@angular/core';
import { VardaVakajarjestajaService } from '../../core/services/varda-vakajarjestaja.service';

@Directive({
    selector: '[appToimipaikkaNimi]',
    standalone: false
})
export class ToimipaikkaNimiDirective implements AfterContentInit {
  private elem: HTMLInputElement;

  constructor(private vakajarjestajaService: VardaVakajarjestajaService, private el: ElementRef) {
    this.elem = el.nativeElement;
  }

  ngAfterContentInit() {
    if (this.elem.textContent) {
      const toimipaikka_oid = this.elem.textContent.trim();
      const toimipaikat = this.vakajarjestajaService.getFilteredToimipaikat().toimipaikat;
      const foundToimipaikka = toimipaikat.find(toimipaikka => toimipaikka.organisaatio_oid === toimipaikka_oid);
      this.elem.textContent = foundToimipaikka?.nimi || this.elem.textContent;
    }
  }
}
