import { Component, OnInit, OnDestroy } from '@angular/core';
import { UserAccess } from '../../../utilities/models/varda-user-access.model';
import { AuthService } from '../../../core/auth/auth.service';
import { FormArray, FormGroup, FormControl, Validators } from '@angular/forms';
import { environment } from 'projects/virkailija-app/src/environments/environment';
import { LoadingHttpService } from 'varda-shared';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { VardaVakajarjestajaUi } from '../../../utilities/models';
import { Observable, BehaviorSubject, Subscription, forkJoin, of } from 'rxjs';
import { VardaTilapainenHenkiloDTO } from '../../../utilities/models/dto/varda-tilapainen-henkilo-dto.model';
import { VardaHenkilostoService } from '../../../core/services/varda-henkilosto-service';
import { delay } from 'rxjs/internal/operators/delay';
import { MatDialog } from '@angular/material/dialog';
import { EiHenkilostoaDialogComponent } from './ei-henkilostoa-dialog/ei-henkilostoa-dialog.component';
import { flatMap, catchError } from 'rxjs/operators';
import { Router } from '@angular/router';

@Component({
  selector: 'app-varda-henkilosto-tilapainen',
  templateUrl: './varda-henkilosto-tilapainen.component.html',
  styleUrls: ['./varda-henkilosto-tilapainen.component.css']
})
export class VardaHenkilostoTilapainenComponent implements OnDestroy {
  private START_YEAR = 2018;
  private disableEditingAfterMonthNr = 5;
  lastEditableYear: number;
  toimijaAccess: UserAccess;
  monthArray = new FormArray([]);
  henkilostoKytkin = { value: false, hidden: false, editable: true };
  vuosiArvot = { hours: 0, employees: 0, months: 0 };
  lastUpdated: string;
  henkilostoVuosi: number;
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  isLoading: Observable<boolean>;


  vuodet: Array<number> = [];
  constructor(
    private dialog: MatDialog,
    private vakajarjestajaService: VardaVakajarjestajaService,
    private http: LoadingHttpService,
    private authService: AuthService,
    private henkilostoService: VardaHenkilostoService,
    private router: Router
  ) {

    this.isLoading = this.http.isLoading();
    this.selectedVakajarjestaja = vakajarjestajaService.getSelectedVakajarjestaja();
    this.toimijaAccess = this.authService.getUserAccess();

    if (!this.toimijaAccess.tilapainenHenkilosto.katselija) {
      this.router.navigate(['/']);
    }

    this.initiateYears();
  }

  ngOnDestroy() { }

  initiateMonths(year: number) {
    const months = [
      'aika.tammikuu',
      'aika.helmikuu',
      'aika.maaliskuu',
      'aika.huhtikuu',
      'aika.toukokuu',
      'aika.kesäkuu',
      'aika.heinäkuu',
      'aika.elokuu',
      'aika.syyskuu',
      'aika.lokakuu',
      'aika.marraskuu',
      'aika.joulukuu',
    ];
    this.lastUpdated = '';
    this.henkilostoKytkin = { value: false, editable: true, hidden: false };
    this.vuosiArvot = { hours: 0, employees: 0, months: 0 };

    this.henkilostoService.getTilapainenHenkilostoByYear(year, this.selectedVakajarjestaja.organisaatio_oid).subscribe(data => {
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
          lahdejarjestelma: '1',
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
            tuntimaara: new FormControl(result.tuntimaara, [Validators.pattern('^\\d+([,.]\\d{1,2})?$'), Validators.max(38.83), Validators.required]),
            tyontekijamaara: new FormControl(result.tyontekijamaara, [Validators.pattern('^\\d+$'), Validators.required]),
            vakajarjestaja_oid: new FormControl(this.selectedVakajarjestaja.organisaatio_oid),
            lahdejarjestelma: new FormControl(1)
          }));
        } else {
          this.henkilostoKytkin.hidden = true;
        }
      });

      if (!this.monthArray.controls.some(formGroup =>
        parseInt(formGroup.get('tuntimaara').value) !== 0 || parseInt(formGroup.get('tyontekijamaara').value) !== 0)) {
        this.henkilostoKytkin.value = true;
      }

      if (year < this.lastEditableYear || !this.toimijaAccess.tilapainenHenkilosto.tallentaja) {
        this.monthArray.disable();
      }

    });
  }

  initiateYears() {
    const today = new Date();
    this.lastEditableYear = 2015; // today.getMonth() > this.disableEditingAfterMonthNr ? today.getUTCFullYear() : today.getUTCFullYear() - 1;

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
    const requestsToSend = formArray.controls.map(formGroup => {
      if (!formGroup.pristine && formGroup.valid) {
        formGroup.markAsPristine();
        return this.henkilostoService.saveTilapainenHenkilostoByMonth(formGroup.value);
      }
      return null;
    }).filter(Boolean);

    forkJoin(requestsToSend).pipe(catchError(err => of(err))).subscribe({
      next: () => this.initiateMonths(this.henkilostoVuosi),
      error: (err) => console.log(err)
    });
  }
}
