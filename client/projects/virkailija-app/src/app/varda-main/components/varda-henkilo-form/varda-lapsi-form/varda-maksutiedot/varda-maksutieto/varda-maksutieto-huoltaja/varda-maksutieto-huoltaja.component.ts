import { Component, Input, OnInit, Output, EventEmitter, ElementRef } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { MatRadioChange } from '@angular/material/radio';
import { ErrorTree, VardaErrorMessageService } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { HuoltajaDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-maksutieto-dto.model';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { Observable } from 'rxjs';
import { TranslateService } from '@ngx-translate/core';

export interface HuoltajaFormResponse {
  index: number;
  formGroup: FormGroup;
}

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
export class VardaMaksutietoHuoltajaComponent implements OnInit {
  @Input() huoltaja: HuoltajaDTO;
  @Input() huoltajaForm: FormGroup;
  @Input() indexNr: number;
  @Input() showDeleteButton: boolean;
  @Output() removeHuoltaja = new EventEmitter<number>(true);

  i18n = VirkailijaTranslations;
  element: ElementRef;
  expandPanel: boolean;
  maksutietoFormErrors: Observable<Array<ErrorTree>>;
  private henkilostoErrorService: VardaErrorMessageService;

  constructor(
    private el: ElementRef,
    translateService: TranslateService
  ) {
    this.element = this.el;
    this.henkilostoErrorService = new VardaErrorMessageService(translateService);
    this.maksutietoFormErrors = this.henkilostoErrorService.initErrorList();
  }


  ngOnInit() {
    if (this.huoltajaForm) {
      this.huoltajaForm.controls.henkilo_oid.disable();
    }
  }

  addWithSsnOrOidChanged(radioEvent: MatRadioChange): void {
    if (radioEvent.value) {
      this.huoltajaForm.controls.henkilotunnus.enable();
      this.huoltajaForm.controls.henkilo_oid.disable();
    } else {
      this.huoltajaForm.controls.henkilotunnus.disable();
      this.huoltajaForm.controls.henkilo_oid.enable();
    }
  }

  deleteHuoltaja() {
    this.removeHuoltaja.emit(this.indexNr);
  }
}
