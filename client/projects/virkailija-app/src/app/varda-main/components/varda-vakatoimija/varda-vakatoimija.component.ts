import { Component } from '@angular/core';
import { VardaVakajarjestaja, VardaVakajarjestajaUi } from '../../../utilities/models';
import { FormGroup, FormControl, Validators } from '@angular/forms';
import { VardaFormValidators } from '../../../shared/validators/varda-form-validators';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { AuthService } from '../../../core/auth/auth.service';
import { UserAccess } from '../../../utilities/models/varda-user-access.model';
import { VardaApiService } from '../../../core/services/varda-api.service';
import { ErrorTree, VardaErrorMessageService } from '../../../core/services/varda-error-message.service';
import { BehaviorSubject, Observable } from 'rxjs';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { VardaVakajarjestajaApiService } from '../../../core/services/varda-vakajarjestaja-api.service';
import { TranslateService } from '@ngx-translate/core';
import { EMAIL_REGEX } from '../../../utilities/constants';

@Component({
  selector: 'app-varda-vakatoimija',
  templateUrl: './varda-vakatoimija.component.html',
  styleUrls: ['./varda-vakatoimija.component.css']
})
export class VardaVakatoimijaComponent {
  i18n = VirkailijaTranslations;
  vakatoimijaForm: FormGroup;
  vakatoimijaFormErrors: Observable<Array<ErrorTree>>;
  toimijaAccess: UserAccess;
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  vakajarjestajaDetails: VardaVakajarjestaja;
  isEdit: boolean;
  saveAccess: boolean;
  isLoading = new BehaviorSubject<boolean>(false);
  saveSuccess: boolean;
  private errorService: VardaErrorMessageService;

  constructor(
    private vakajarjestajaService: VardaVakajarjestajaService,
    private vakajarjestajaApiService: VardaVakajarjestajaApiService,
    private vardaApiService: VardaApiService,
    private authService: AuthService,
    translateService: TranslateService
  ) {
    this.errorService = new VardaErrorMessageService(translateService);
    this.vakatoimijaFormErrors = this.errorService.initErrorList();
    this.toimijaAccess = this.authService.getUserAccess();
    this.saveAccess = this.toimijaAccess.toimijatiedot.tallentaja;
    this.selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();

    this.vakajarjestajaApiService.getVakajarjestaja(this.selectedVakajarjestaja.id).subscribe((vakajarjestaja: VardaVakajarjestaja) => {
      this.initVakatoimijaForm(vakajarjestaja);
    });
  }

  initVakatoimijaForm(vakajarjestaja: VardaVakajarjestaja) {
    this.vakajarjestajaDetails = vakajarjestaja;

    this.vakatoimijaForm = new FormGroup({
      sahkopostiosoite: new FormControl(vakajarjestaja.sahkopostiosoite,
        [Validators.required, VardaFormValidators.validStringFormat.bind(null, { regex: EMAIL_REGEX })]),
      puhelinnumero: new FormControl(vakajarjestaja.puhelinnumero, [Validators.required, VardaFormValidators.validStringFormat.bind(null, { regex: '^(\\+358)[1-9]\\d{5,10}$' })]),
    });

    this.disableForm();
  }

  saveVakatoimijaForm(form: FormGroup) {
    form.markAllAsTouched();
    this.errorService.resetErrorList();

    if (VardaErrorMessageService.formIsValid(form)) {
      this.isLoading.next(true);
      const vakatoimijaDTO: VardaVakajarjestaja = { ...form.value };

      this.vakajarjestajaApiService.patchVakajarjestaja(this.selectedVakajarjestaja.id, vakatoimijaDTO).subscribe({
        next: vakatoimijaData => {
          this.disableForm();
          this.saveSuccess = true;
          setTimeout(() => this.saveSuccess = false, 15000);
        },
        error: err => this.errorService.handleError(err)
      }).add(() => setTimeout(() => this.isLoading.next(false), 500));
    }
  }


  enableForm() {
    this.isEdit = true;
    this.vakatoimijaForm.enable();
  }

  disableForm() {
    this.isEdit = false;
    this.vakatoimijaForm.disable();
  }
}
