import { Component, OnDestroy } from '@angular/core';
import { UserAccess } from '../../../utilities/models/varda-user-access.model';
import { AuthService } from '../../../core/auth/auth.service';
import { FormArray, FormGroup, FormControl, Validators } from '@angular/forms';
import { LoadingHttpService } from 'varda-shared';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { VardaVakajarjestajaUi } from '../../../utilities/models';
import { Observable, forkJoin, of } from 'rxjs';
import { VardaTilapainenHenkiloDTO } from '../../../utilities/models/dto/varda-tilapainen-henkilo-dto.model';
import { MatDialog } from '@angular/material/dialog';
import { EiHenkilostoaDialogComponent } from './ei-henkilostoa-dialog/ei-henkilostoa-dialog.component';
import { catchError } from 'rxjs/operators';
import { Router } from '@angular/router';
import { VardaHenkilostoApiService } from '../../../core/services/varda-henkilosto.service';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { ErrorTree, HenkilostoErrorMessageService } from '../../../core/services/varda-henkilosto-error-message.service';
import { Lahdejarjestelma } from '../../../utilities/models/enums/hallinnointijarjestelma';
import { VardaSnackBarService } from '../../../core/services/varda-snackbar.service';

@Component({
  selector: 'app-varda-henkilosto-tilapainen',
  templateUrl: './varda-henkilosto-tilapainen.component.html',
  styleUrls: ['./varda-henkilosto-tilapainen.component.css']
})
export class VardaHenkilostoTilapainenComponent implements OnDestroy {
  private START_YEAR = 2020;
  private disableEditingAfterMonthNr = 5;
  lastEditableYear: number;
  toimijaAccess: UserAccess;
  monthArray = new FormArray([]);
  henkilostoKytkin = { value: false, hidden: false, editable: true };
  vuosiArvot = { hours: 0, employees: 0, months: 0 };
  vuodet: Array<number> = [];
  lastUpdated: string;
  henkilostoVuosi: number;

  selectedVakajarjestaja: VardaVakajarjestajaUi;
  isLoading$: Observable<boolean>;
  i18n = VirkailijaTranslations;
  henkilostoFormErrors: Observable<Array<ErrorTree>>;
  private henkilostoErrorService = new HenkilostoErrorMessageService();

  constructor(
    private dialog: MatDialog,
    private vakajarjestajaService: VardaVakajarjestajaService,
    private http: LoadingHttpService,
    private authService: AuthService,
    private henkilostoService: VardaHenkilostoApiService,
    private router: Router,
    private snackBarService: VardaSnackBarService,
  ) {

    this.isLoading$ = this.http.isLoading();
    this.selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();
    this.toimijaAccess = this.authService.getUserAccess();

    if (!this.toimijaAccess.tilapainenHenkilosto.katselija) {
      this.router.navigate(['/']);
    }
    this.henkilostoFormErrors = this.henkilostoErrorService.initErrorList();
    this.initiateYears();
  }

  ngOnDestroy() { }

  initiateMonths(year: number) {
    const months = [
      this.i18n.aika_tammikuu,
      this.i18n.aika_helmikuu,
      this.i18n.aika_maaliskuu,
      this.i18n.aika_huhtikuu,
      this.i18n.aika_toukokuu,
      this.i18n.aika_kesäkuu,
      this.i18n.aika_heinäkuu,
      this.i18n.aika_elokuu,
      this.i18n.aika_syyskuu,
      this.i18n.aika_lokakuu,
      this.i18n.aika_marraskuu,
      this.i18n.aika_joulukuu,
    ];
    this.lastUpdated = '';
    this.henkilostoKytkin = { value: false, editable: true, hidden: false };
    this.vuosiArvot = { hours: 0, employees: 0, months: 0 };

    this.henkilostoService.getTilapainenHenkilostoByYear(year, this.selectedVakajarjestaja.organisaatio_oid).subscribe({
      next: data => {
        const results: Array<VardaTilapainenHenkiloDTO> = data.results;
        this.monthArray = new FormArray([]);

        months.forEach((month, index) => {
          // block first 8 months on the start year. this filter can be removed 3/2021
          if (`${year}` === this.START_YEAR.toString() && index < 8) {
            return;
          }

          const thisMonth = new Date().toISOString().substr(0, 7);
          const yymm = new Date(Date.UTC(year, index, 1)).toISOString().substr(0, 7);
          const result = results.find(res => res.kuukausi.startsWith(yymm)) || {
            id: null,
            kuukausi: `${yymm}-01`,
            tuntimaara: null,
            tyontekijamaara: null,
            vakajarjestaja_oid: this.selectedVakajarjestaja.organisaatio_oid,
            lahdejarjestelma: Lahdejarjestelma.kayttoliittyma,
            url: null
          };

          if (result.tuntimaara !== null || result.tyontekijamaara !== null) {
            this.henkilostoKytkin.editable = false;
            this.vuosiArvot.months++;
            this.vuosiArvot.employees += parseInt(`${result.tyontekijamaara}`) || 0;
            this.vuosiArvot.hours += parseInt(`${result.tuntimaara}`) || 0;
          }

          if (result.muutos_pvm && result.muutos_pvm > this.lastUpdated) {
            this.lastUpdated = result.muutos_pvm;
          }


          if (yymm <= thisMonth) {
            this.monthArray.push(new FormGroup({
              id: new FormControl(result.id),
              name: new FormControl(month),
              url: new FormControl(result.url),
              kuukausi: new FormControl(result.kuukausi),
              tuntimaara: new FormControl(result.tuntimaara, [...this.tuntimaaraValidators()]),
              tyontekijamaara: new FormControl(result.tyontekijamaara, [...this.tyontekijamaaraValidators()]),
              vakajarjestaja_oid: new FormControl(this.selectedVakajarjestaja.organisaatio_oid),
              lahdejarjestelma: new FormControl(Lahdejarjestelma.kayttoliittyma)
            }));
          } else {
            this.henkilostoKytkin.hidden = true;
          }
        });

        if (!this.monthArray.controls.some(formGroup =>
          parseInt(formGroup.get('tuntimaara').value) !== 0 || parseInt(formGroup.get('tyontekijamaara').value) !== 0)) {
          this.henkilostoKytkin.value = this.monthArray.controls.length === 12;
        }

        if (year < this.lastEditableYear || !this.toimijaAccess.tilapainenHenkilosto.tallentaja) {
          this.monthArray.disable();
        }

      }, error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
    });
  }

  initiateYears() {
    const today = new Date();
    this.lastEditableYear = today.getMonth() > this.disableEditingAfterMonthNr ? today.getUTCFullYear() : today.getUTCFullYear() - 1;

    for (let i = this.START_YEAR; i <= today.getUTCFullYear(); ++i) {
      this.vuodet.push(i);
    }
    this.henkilostoVuosi = today.getUTCFullYear();
    this.initiateMonths(this.henkilostoVuosi);
  }


  toggleHenkilosto() {
    if (this.monthArray.disabled) {
      return;
    }

    if (!this.henkilostoKytkin.value) {
      if (this.henkilostoKytkin.editable) {
        const dialogRef = this.dialog.open(EiHenkilostoaDialogComponent, {});

        dialogRef.afterClosed().subscribe(result => {
          if (result) {
            this.henkilostoKytkin.value = !this.henkilostoKytkin.value;
            this.monthArray.controls.map(formGroup => {
              formGroup.get('tuntimaara').setValue(0);
              formGroup.get('tyontekijamaara').setValue(0);
              formGroup.markAsDirty();
            });

            this.saveHenkilosto(this.monthArray);
          }
        });
      }
    } else {
      this.henkilostoKytkin.value = !this.henkilostoKytkin.value;
    }
  }

  saveHenkilosto(formArray: FormArray) {
    const requestsToSend = formArray.controls.filter(formGroup => formGroup.valid).map(formGroup => {
      if (!formGroup.pristine) {
        formGroup.markAsPristine();
        return this.henkilostoService.saveTilapainenHenkilostoByMonth(formGroup.value);
      }
      return null;
    }).filter(Boolean);

    forkJoin(requestsToSend).pipe(catchError(err => {
      this.henkilostoErrorService.handleError(err);
      return of(err);
    })).subscribe({
      next: () => {
        this.initiateMonths(this.henkilostoVuosi);
        this.snackBarService.success(this.i18n.tilapainen_henkilosto_save_success);
      },
      error: (err) => this.henkilostoErrorService.handleError(err, this.snackBarService)
    });
  }


  valueChanged(month: FormControl) {
    const tuntimaara = month.get('tuntimaara');
    const tyontekijamaara = month.get('tyontekijamaara');

    if ((tuntimaara.value <= 0 || tyontekijamaara.value <= 0) && (tuntimaara.value > 0 || tyontekijamaara.value > 0)) {
      tuntimaara.setValidators([...this.tuntimaaraValidators(), Validators.max(0)]);
      tyontekijamaara.setValidators([...this.tyontekijamaaraValidators(), Validators.max(0)]);
    } else {
      tuntimaara.setValidators([...this.tuntimaaraValidators()]);
      tyontekijamaara.setValidators([...this.tyontekijamaaraValidators()]);
    }

    tuntimaara.updateValueAndValidity();
    tyontekijamaara.updateValueAndValidity();
  }

  private tuntimaaraValidators() {
    return [Validators.pattern('^\\d+([,.]\\d{1,2})?$'), Validators.required, Validators.min(0)];
  }

  private tyontekijamaaraValidators() {
    return [Validators.pattern('^\\d+$'), Validators.required, Validators.min(0)];
  }
}
