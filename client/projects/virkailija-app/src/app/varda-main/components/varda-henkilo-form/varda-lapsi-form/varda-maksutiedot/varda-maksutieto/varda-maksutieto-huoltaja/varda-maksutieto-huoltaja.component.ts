import { Component, Input, Output, EventEmitter, ElementRef, SimpleChanges, OnChanges } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { MatLegacyRadioChange as MatRadioChange } from '@angular/material/legacy-radio';
import { ErrorTree, VardaErrorMessageService } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { Observable } from 'rxjs';
import { TranslateService } from '@ngx-translate/core';
import { HuoltajaDTO } from '../../../../../../../utilities/models/dto/varda-lapsi-dto.model';

@Component({
  selector: 'app-varda-maksutieto-huoltaja',
  templateUrl: './varda-maksutieto-huoltaja.component.html',
  styleUrls: [
    './varda-maksutieto-huoltaja.component.css',
    '../varda-maksutieto.component.css',
    '../../varda-maksutiedot.component.css',
    '../../../varda-lapsi-form.component.css',
    '../../../../varda-henkilo-form.component.css'
  ]
})
export class VardaMaksutietoHuoltajaComponent implements OnChanges {
  @Input() huoltaja: HuoltajaDTO;
  @Input() huoltajaForm: FormGroup;
  @Input() indexNr: number;
  @Input() showDeleteButton: boolean;
  @Output() removeHuoltaja = new EventEmitter<number>(true);

  i18n = VirkailijaTranslations;
  element: ElementRef;
  maksutietoFormErrors: Observable<Array<ErrorTree>>;

  private errorMessageService: VardaErrorMessageService;

  constructor(
    private el: ElementRef,
    translateService: TranslateService
  ) {
    this.element = this.el;
    this.errorMessageService = new VardaErrorMessageService(translateService);
    this.maksutietoFormErrors = this.errorMessageService.initErrorList();
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes.huoltajaForm) {
      this.changeIdentifierControlState(this.huoltajaForm.controls.addWithSsnOrOid.value);
    }
  }

  addWithSsnOrOidChanged(radioEvent: MatRadioChange): void {
    this.changeIdentifierControlState(radioEvent.value);
  }

  changeIdentifierControlState(addWithSsn: boolean) {
    setTimeout(() => {
      // https://github.com/angular/angular/issues/22556
      if (addWithSsn === true) {
        this.huoltajaForm.controls.henkilotunnus.enable();
        this.huoltajaForm.controls.henkilo_oid.disable();
      } else {
        this.huoltajaForm.controls.henkilotunnus.disable();
        this.huoltajaForm.controls.henkilo_oid.enable();
      }
    });
  }

  deleteHuoltaja() {
    this.removeHuoltaja.emit(this.indexNr);
  }
}
