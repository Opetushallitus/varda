import { Component, OnInit } from '@angular/core';
import { UserAccess } from '../../../utilities/models/varda-user-access.model';
import { AuthService } from '../../../core/auth/auth.service';
import { FormArray, FormGroup, FormControl, Validators } from '@angular/forms';
import { LoadingHttpService, VardaDateService } from 'varda-shared';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { VardaVakajarjestaja, VardaVakajarjestajaUi } from '../../../utilities/models';
import { Observable, forkJoin, of } from 'rxjs';
import { MatDialog } from '@angular/material/dialog';
import { EiHenkilostoaDialogComponent } from './ei-henkilostoa-dialog/ei-henkilostoa-dialog.component';
import { catchError } from 'rxjs/operators';
import { VardaHenkilostoApiService } from '../../../core/services/varda-henkilosto.service';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { ErrorTree, VardaErrorMessageService } from '../../../core/services/varda-error-message.service';
import { Lahdejarjestelma } from '../../../utilities/models/enums/hallinnointijarjestelma';
import { VardaSnackBarService } from '../../../core/services/varda-snackbar.service';
import { TranslateService } from '@ngx-translate/core';
import { VardaVakajarjestajaApiService } from '../../../core/services/varda-vakajarjestaja-api.service';

enum TilapainenPrefix {
  spring = VirkailijaTranslations.tilapainen_henkilosto_first_half,
  autumn = VirkailijaTranslations.tilapainen_henkilosto_last_half
}

interface TilapainenYearPicker {
  earliest: number;
  latest: number;
  year: number;
  prefix: TilapainenPrefix;
}

@Component({
  selector: 'app-varda-henkilosto-tilapainen',
  templateUrl: './varda-henkilosto-tilapainen.component.html',
  styleUrls: ['./varda-henkilosto-tilapainen.component.css']
})
export class VardaHenkilostoTilapainenComponent implements OnInit {
  toimijaAccess: UserAccess;
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  isSubmitting: Observable<boolean>;
  i18n = VirkailijaTranslations;
  henkilostoFormErrors: Observable<Array<ErrorTree>>;
  lastAllowedDate: Date;
  isEdit: boolean;
  monthArray = new FormArray([]);
  vuodet: Array<TilapainenYearPicker> = [];
  vuosiArvot = { hours: 0, employees: 0, months: 0 };
  henkilostoVuosi: TilapainenYearPicker;
  henkilostoKytkin = { value: false, disabled: true };
  lastUpdated: string;

  months = [
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

  private henkilostoErrorService: VardaErrorMessageService;

  constructor(
    private dialog: MatDialog,
    private vakajarjestajaService: VardaVakajarjestajaService,
    private vakajarjestajaApiService: VardaVakajarjestajaApiService,
    private http: LoadingHttpService,
    private authService: AuthService,
    private henkilostoService: VardaHenkilostoApiService,
    private snackBarService: VardaSnackBarService,
    translateService: TranslateService
  ) {
    this.isSubmitting = this.http.isLoading();
    this.selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();
    this.henkilostoErrorService = new VardaErrorMessageService(translateService);
    this.henkilostoFormErrors = this.henkilostoErrorService.initErrorList();



  }

  ngOnInit() {
    this.toimijaAccess = this.authService.getUserAccess();
    this.vakajarjestajaApiService.getVakajarjestaja(this.selectedVakajarjestaja.id).subscribe((vakajarjestajaData: VardaVakajarjestaja) => {
      this.initiateYears(vakajarjestajaData);
    });
  }

  initiateYears(vakajarjestaja: VardaVakajarjestaja) {
    const july = 6;
    const today = new Date();
    const seasonEndingDate = today.getMonth() < july ? new Date(today.getUTCFullYear(), 5, 30) : new Date(today.getUTCFullYear(), 11, 31);
    const vakajarjestajaStartDate = vakajarjestaja.alkamis_pvm ? new Date(vakajarjestaja.alkamis_pvm) : VardaDateService.henkilostoReleaseDate;
    const lastAllowedDate = vakajarjestaja.paattymis_pvm ? new Date(vakajarjestaja.paattymis_pvm) : seasonEndingDate;

    let earliestAllowedDate = VardaDateService.henkilostoReleaseDate;

    if (vakajarjestajaStartDate > earliestAllowedDate) {
      earliestAllowedDate = vakajarjestajaStartDate;
    }

    for (let i = earliestAllowedDate.getUTCFullYear(); i <= lastAllowedDate.getUTCFullYear(); ++i) {
      for (let j = 0; j < 2; j++) {
        const monthComparison = j * july;
        const pickerData: TilapainenYearPicker = {
          earliest: monthComparison,
          latest: monthComparison + 5,
          year: i,
          prefix: monthComparison < july ? TilapainenPrefix.spring : TilapainenPrefix.autumn
        };

        if (i === earliestAllowedDate.getUTCFullYear()) {
          pickerData.earliest = earliestAllowedDate.getMonth();
          // skip first half of the year as the first allowed month is august or later
          if (j === 0 && pickerData.earliest >= july) {
            continue;
          }
        }

        if (i === lastAllowedDate.getUTCFullYear()) {
          const lastAllowedMonth = lastAllowedDate.getMonth();
          pickerData.latest = lastAllowedMonth < pickerData.latest ? lastAllowedMonth : pickerData.latest;
          // skip last half of the year as the last allowed month is before august
          if (j === 1 && lastAllowedMonth < july) {
            continue;
          }
        }

        this.vuodet.push(pickerData);
      }
    }

    this.vuodet.reverse();
    this.henkilostoVuosi = this.vuodet?.[0];
    this.initiateMonths(this.henkilostoVuosi);
  }

  initiateMonths(vuosi: TilapainenYearPicker) {
    this.lastUpdated = null;
    const today = new Date();
    const lastAllowedMonth = today.toISOString().substr(0, 7);
    this.monthArray = new FormArray([]);
    this.henkilostoKytkin.disabled = false;
    this.vuosiArvot = { hours: 0, employees: 0, months: 0 };
    const tyontekijatByMonth = [];

    if (!this.toimijaAccess.tilapainenHenkilosto.tallentaja) {
      this.henkilostoKytkin.disabled = true;
    }

    this.henkilostoService.getTilapainenHenkilostoByYear(vuosi.year, this.selectedVakajarjestaja.organisaatio_oid).subscribe({
      next: data => {
        for (let month = vuosi.earliest; month <= vuosi.latest; ++month) {
          const yymm = new Date(Date.UTC(vuosi.year, month, 1)).toISOString().substr(0, 7);
          const monthData = data.results.find(res => res.kuukausi.startsWith(yymm)) || {
            id: null,
            url: null,
            kuukausi: `${yymm}-01`,
            tuntimaara: null,
            tyontekijamaara: null,
            vakajarjestaja_oid: this.selectedVakajarjestaja.organisaatio_oid,
            lahdejarjestelma: Lahdejarjestelma.kayttoliittyma,
            muutos_pvm: ''
          };

          const formGroup = new FormGroup({
            id: new FormControl(monthData.id),
            name: new FormControl(this.months[month]),
            url: new FormControl(monthData.url),
            kuukausi: new FormControl(monthData.kuukausi),
            tuntimaara: new FormControl(monthData.tuntimaara, [...this.tuntimaaraValidators()]),
            tyontekijamaara: new FormControl(monthData.tyontekijamaara, [...this.tyontekijamaaraValidators()]),
            vakajarjestaja_oid: new FormControl(monthData.vakajarjestaja_oid),
            lahdejarjestelma: new FormControl(monthData.lahdejarjestelma),
            readonly: new FormControl(yymm > lastAllowedMonth)
          });

          this.monthArray.push(formGroup);

          if (!this.lastUpdated && monthData?.muutos_pvm || monthData?.muutos_pvm > this.lastUpdated) {
            this.lastUpdated = monthData.muutos_pvm;
          }

          if (monthData.tyontekijamaara !== null) {
            tyontekijatByMonth.push(monthData.tyontekijamaara);
            this.vuosiArvot.employees += monthData.tyontekijamaara || 0;
            this.vuosiArvot.hours += parseFloat(`${monthData.tuntimaara}`) || 0;
          }
        }

        this.vuosiArvot.months = tyontekijatByMonth.length;
        this.henkilostoKytkin.value = !!tyontekijatByMonth.length && tyontekijatByMonth.reduce((a, b) => a + b, 0) === 0;

        this.disableForm();
        if (!tyontekijatByMonth.length) {
          this.enableForm();
        }

      }, error: err => this.henkilostoErrorService.handleError(err, this.snackBarService)
    });
  }

  toggleHenkilosto() {
    if (this.henkilostoKytkin.disabled) {
      return;
    }

    if (this.henkilostoKytkin.value) {
      const dialogRef = this.dialog.open(EiHenkilostoaDialogComponent, {});
      dialogRef.afterClosed().subscribe(result => {
        if (result) {
          this.monthArray.enable();
          this.monthArray.controls.map(formGroup => {
            formGroup.get('tuntimaara').setValue(0);
            formGroup.get('tyontekijamaara').setValue(0);
            formGroup.markAsDirty();
          });

          this.saveHenkilosto(this.monthArray);
        } else {
          this.henkilostoKytkin.value = false;
        }
      });

    } else {
      this.enableForm();
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

  disableForm() {
    this.isEdit = false;
    this.monthArray.disable();
  }

  enableForm() {
    if (!this.henkilostoKytkin.disabled) {
      this.isEdit = true;
      this.monthArray.enable();
    }
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
