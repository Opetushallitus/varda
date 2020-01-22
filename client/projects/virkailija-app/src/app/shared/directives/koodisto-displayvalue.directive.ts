import { Directive, ElementRef, HostListener, OnInit, Input } from '@angular/core';
import { NgControl, Validators } from '@angular/forms';
import { VardaKielikoodistoService } from '../../core/services/varda-kielikoodisto.service';
import { VardaKoodistot } from '../../utilities/models';
import { VardaKuntakoodistoService } from '../../core/services/varda-kuntakoodisto.service';
import { TranslateService } from '@ngx-translate/core';

@Directive({
  selector: '[appKoodistoDisplayvalue]'
})
export class KoodistoDisplayvalueDirective implements OnInit {

    @Input() options: Array<any>;
    @Input() koodisto: string;

    private elem: HTMLInputElement;

    constructor(private el: ElementRef,
        private control: NgControl,
        private vardaKielikoodistoService: VardaKielikoodistoService,
        private vardaKuntakoodistoService: VardaKuntakoodistoService,
        private translateService: TranslateService) {
        this.elem = el.nativeElement;
    }

    initKoodistoOptionSelection(): void {
        if (this.control.value) {
            const strValue = this.control.value;
            if (!strValue) {
                this.control.control.setErrors(null);
                return;
            }
            const strToSearch = strValue.toUpperCase();
            let optionFound;

            if (this.koodisto === VardaKoodistot.KIELIKOODISTO) {
                optionFound = this.vardaKielikoodistoService.getKielikoodistoOptionByLangAbbreviation(strToSearch);
            } else if (this.koodisto === VardaKoodistot.KUNTAKOODISTO) {
                optionFound = this.vardaKuntakoodistoService.getKuntakoodistoOptionByKuntakoodi(strToSearch);
            }

            if (optionFound) {
                this.control.control.setValue(optionFound);
                let metadata;
                if (this.koodisto === VardaKoodistot.KIELIKOODISTO) {
                    metadata = this.vardaKielikoodistoService.getKielikoodistoOptionMetadataByLang(optionFound.metadata,
                        this.translateService.currentLang);
                } else if (this.koodisto === VardaKoodistot.KUNTAKOODISTO) {
                    metadata = this.vardaKuntakoodistoService.getKuntaKoodistoOptionMetadataByLang(optionFound.metadata,
                        this.translateService.currentLang);
                }
                this.control.valueAccessor.writeValue(metadata.nimi);
            }
        }
    }

    checkKoodistoOptionSelection(): void {
        if (this.control.value && this.control.value['koodiArvo']) {

            const optionMetadata = this.control.value['metadata'];
            let metadata;
            if (this.koodisto === VardaKoodistot.KIELIKOODISTO) {
                metadata = this.vardaKielikoodistoService.getKielikoodistoOptionMetadataByLang(optionMetadata,
                    this.translateService.currentLang);
            } else if (this.koodisto === VardaKoodistot.KUNTAKOODISTO) {
                metadata = this.vardaKuntakoodistoService.getKuntaKoodistoOptionMetadataByLang(optionMetadata,
                    this.translateService.currentLang);
            }
            this.control.valueAccessor.writeValue(metadata.nimi);
        }
    }

    ngOnInit() {
        if (this.koodisto === VardaKoodistot.KIELIKOODISTO || this.koodisto === VardaKoodistot.KUNTAKOODISTO) {
            this.initKoodistoOptionSelection();
        }
        this.control.valueChanges.subscribe(() => {
            if (this.koodisto === VardaKoodistot.KIELIKOODISTO || this.koodisto === VardaKoodistot.KUNTAKOODISTO) {
                this.checkKoodistoOptionSelection();
            }
        });
    }
}
