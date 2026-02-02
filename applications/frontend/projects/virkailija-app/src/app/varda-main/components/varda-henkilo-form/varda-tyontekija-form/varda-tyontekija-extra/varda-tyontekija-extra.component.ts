import {Component, Input, OnDestroy, OnInit} from '@angular/core';
import { VirkailijaTranslations } from '../../../../../../assets/i18n/virkailija-translations.enum';
import { finalize, Observable, Subscription } from 'rxjs';
import { ErrorTree, VardaErrorMessageService } from '../../../../../core/services/varda-error-message.service';
import { FormControl, FormGroup } from '@angular/forms';
import { VardaHenkilostoApiService } from '../../../../../core/services/varda-henkilosto.service';
import { VardaSnackBarService } from '../../../../../core/services/varda-snackbar.service';
import { TranslateService } from '@ngx-translate/core';
import { TyontekijaKooste } from '../../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { UserAccess } from '../../../../../utilities/models/varda-user-access.model';
import { AuthService } from '../../../../../core/auth/auth.service';
import { VardaFormValidators } from '../../../../../shared/validators/varda-form-validators';
import { EMAIL_REGEX } from '../../../../../utilities/constants';
import { VardaModalService } from '../../../../../core/services/varda-modal.service';
import { distinctUntilChanged, filter } from 'rxjs/operators';

@Component({
    selector: 'app-varda-tyontekija-extra',
    templateUrl: './varda-tyontekija-extra.component.html',
    styleUrls: [
        './varda-tyontekija-extra.component.css',
        '../varda-tyontekija-form.component.css',
        '../../varda-henkilo-form.component.css'
    ],
    standalone: false
})
export class VardaTyontekijaExtraComponent implements OnInit, OnDestroy {
  @Input() toimipaikkaAccess: UserAccess;

  i18n = VirkailijaTranslations;
  formErrors: Observable<Array<ErrorTree>>;
  isSubmitting = false;
  formGroup: FormGroup;
  userAccess: UserAccess;
  isEdit = false;

  tyontekijaKooste: TyontekijaKooste;

  private errorService: VardaErrorMessageService;
  private subscriptions: Array<Subscription> = [];

  constructor(
    private henkilostoService: VardaHenkilostoApiService,
    private snackBarService: VardaSnackBarService,
    private authService: AuthService,
    private modalService: VardaModalService,
    translateService: TranslateService
  ) {
    this.errorService = new VardaErrorMessageService(translateService);
    this.formErrors = this.errorService.initErrorList();
  }

  ngOnInit() {
    this.userAccess = this.authService.anyUserAccess;
    this.tyontekijaKooste = this.henkilostoService.activeTyontekija.getValue();
    this.initForm();

    this.subscriptions.push(
      this.formGroup.statusChanges
        .pipe(filter(() => !this.formGroup.pristine), distinctUntilChanged())
        .subscribe(() => this.modalService.setFormValuesChanged(true))
    );
  }

  initForm() {
    this.formGroup = new FormGroup({
      sahkopostiosoite: new FormControl(this.tyontekijaKooste.sahkopostiosoite,
        VardaFormValidators.validStringFormat.bind(null, {regex: EMAIL_REGEX}))
    });
  }

  saveExtra(form: FormGroup) {
    this.isSubmitting = true;
    this.errorService.resetErrorList();
    form.markAllAsTouched();

    if (VardaErrorMessageService.formIsValid(form)) {
      this.subscriptions.push(
        this.henkilostoService.updateTyontekija(this.tyontekijaKooste.id, {...form.value}).pipe(
          finalize(() => this.disableSubmit())
        ).subscribe({
          next: result => {
            this.snackBarService.success(this.i18n.tyontekija_extra_save_success);
            this.henkilostoService.sendHenkilostoListUpdate();
            this.tyontekijaKooste.sahkopostiosoite = result.sahkopostiosoite;
            this.disableForm();
          },
          error: err => this.errorService.handleError(err, this.snackBarService)
        })
      );
    } else {
      this.disableSubmit();
    }
  }

  updateActiveTyontekija() {
    const activeTyontekija = this.henkilostoService.activeTyontekija.getValue();
    this.henkilostoService.activeTyontekija.next(
      {...activeTyontekija, sahkopostiosoite: this.tyontekijaKooste.sahkopostiosoite}
    );
  }

  enableForm() {
    this.isEdit = true;
    this.formGroup.enable();
  }

  disableForm() {
    this.isEdit = false;
    this.formGroup.disable();
    this.initForm();
    this.modalService.setFormValuesChanged(false);
  }

  disableSubmit() {
    setTimeout(() => this.isSubmitting = false, 500);
  }

  ngOnDestroy() {
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
  }
}
