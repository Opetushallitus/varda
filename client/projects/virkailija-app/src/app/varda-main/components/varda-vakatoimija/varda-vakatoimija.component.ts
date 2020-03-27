import { Component, OnInit } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { VardaField, VardaKayttooikeusRoles } from '../../../utilities/models';
import { FormGroup, FormControl, Validators } from '@angular/forms';
import { VardaFormValidators } from '../../../shared/validators/varda-form-validators';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { VardaApiWrapperService } from '../../../core/services/varda-api-wrapper.service';
import { VardaUtilityService } from '../../../core/services/varda-utility.service';
import { AuthService } from '../../../core/auth/auth.service';
import { VardaErrorMessageService } from '../../../core/services/varda-error-message.service';

@Component({
  selector: 'app-varda-vakatoimija',
  templateUrl: './varda-vakatoimija.component.html',
  styleUrls: ['./varda-vakatoimija.component.css']
})
export class VardaVakatoimijaComponent implements OnInit {

  vakatoimijaForm: FormGroup;
  vakatoimijaNimi: string;
  ui: {
    isSubmitting: boolean,
    activeInstructionText: string,
    vakatoimijaSaveSuccess: boolean,
    vakatoimijaSaveError: boolean,
    vakatoimijaSaveSuccessMsg: string,
    vakatoimijaSaveErrorMsg: string,
    vakatoimijaSaveErrors: Array<any>,
    hadValuesOnInit: boolean
  };

  isKatselija: boolean;

  constructor(
    private translateService: TranslateService,
    private vakajarjestajaService: VardaVakajarjestajaService,
    private vardaApiWrapperService: VardaApiWrapperService,
    private vardaUtilityService: VardaUtilityService,
    private authService: AuthService,
    private vardaErrorMessageService: VardaErrorMessageService) {
    this.vakatoimijaNimi = '';
    this.ui = {
      isSubmitting: false,
      activeInstructionText: '',
      vakatoimijaSaveSuccess: false,
      vakatoimijaSaveError: false,
      vakatoimijaSaveErrorMsg: 'alert.modal-generic-save-error',
      vakatoimijaSaveSuccessMsg: 'alert.modal-generic-save-success',
      vakatoimijaSaveErrors: [],
      hadValuesOnInit: false
    };

    this.vakajarjestajaService.getSelectedVakajarjestajaObs().subscribe((data) => {
      if (data.onVakajarjestajaChange) {
        this.initKayttooikeudet();
        this.initVakatoimijaForm();
      }
    });

    this.authService.loggedInUserKayttooikeudetSubject.asObservable().subscribe(() => {
      this.initKayttooikeudet();
    });
  }

  getDisplayName(field: VardaField): string {
    let rv = '';
    const lang = this.translateService.currentLang.toUpperCase();
    const prop = (lang === 'SV') ? 'displayNameSv' : 'displayNameFi';

    if (field.displayName && field.displayName[prop]) {
      rv = field.displayName[prop];
    }
    return rv;
  }

  initKayttooikeudet(): void {
    const kayttooikeusToEvaluate = this.authService.loggedInUserCurrentKayttooikeus;
    if (kayttooikeusToEvaluate === VardaKayttooikeusRoles.VARDA_TALLENTAJA) {
      this.isKatselija = false;
    } else {
      this.isKatselija = true;
    }
  }

  initVakatoimijaForm(): void {
    const selectedVakajarjestaja = this.vakajarjestajaService.selectedVakajarjestaja;
    const selectedVakajarjestajaId = selectedVakajarjestaja.id;

    this.vardaApiWrapperService.getVakaJarjestajaById(selectedVakajarjestajaId).subscribe((vk) => {
      const vakajarjestaja = vk;
      this.vakatoimijaNimi = vakajarjestaja.nimi;
      let sahkopostiosoiteVal, tilinumeroVal, puhelinnumeroVal;

      if (vakajarjestaja) {
        sahkopostiosoiteVal = vakajarjestaja.sahkopostiosoite;
        tilinumeroVal = vakajarjestaja.tilinumero;
        puhelinnumeroVal = vakajarjestaja.puhelinnumero;
      }

      this.vakatoimijaForm = new FormGroup({
        sahkopostiosoite: new FormControl(sahkopostiosoiteVal,
          [Validators.required, VardaFormValidators.validStringFormat.bind(null, {regex: '^[_A-Za-z0-9-+!#$%&\'*/=?^`{|}~]+(\\.[_A-Za-z0-9-+!#$%&\'*/=?^`{|}~]+)*@[A-Za-z0-9][A-Za-z0-9-]+(\\.[A-Za-z0-9-]+)*(\\.[A-Za-z]{2,})$'})]),
        tilinumero: new FormControl(tilinumeroVal, VardaFormValidators.validOrEmptyIBAN),
        puhelinnumero: new FormControl(puhelinnumeroVal, [Validators.required, VardaFormValidators.validStringFormat.bind(null, {regex: '^\\+358\\d+$'})])
      });

      this.ui.hadValuesOnInit = Object.values(this.vakatoimijaForm.value).some((v) => v ? true : false);
    });
  }

  isTouched(fieldName: string): boolean {
    if (this.vakatoimijaForm) {
      let rv;
      if (this.ui.hadValuesOnInit) {
        rv = true;
      } else {
        rv = this.vakatoimijaForm.get(fieldName).touched;
      }
      return rv;
    }
  }

  onBlur(): void {
    this.ui.activeInstructionText = '';
  }

  onFocus(field: string): void {
    this.ui.activeInstructionText = field;
  }

  onSaveError(e: any): void {
    const errorMessageObj = this.vardaErrorMessageService.getErrorMessages(e);
    this.ui.vakatoimijaSaveErrors = errorMessageObj.errorsArr;
    this.ui.vakatoimijaSaveError = true;
    this.ui.isSubmitting = false;
  }

  saveVakatoimijaForm(): void {
    this.ui.vakatoimijaSaveSuccess = false;
    this.ui.vakatoimijaSaveError = false;
    this.ui.isSubmitting = true;
    const vakatoimijaFormData = this.vakatoimijaForm.value;
    this.vardaApiWrapperService.saveVakatoimijaData(vakatoimijaFormData).subscribe(() => {
      this.ui.vakatoimijaSaveSuccess = true;
      this.ui.isSubmitting = false;
    }, this.onSaveError.bind(this));
  }

  ngOnInit() {
    this.initKayttooikeudet();
    this.initVakatoimijaForm();
  }

}
