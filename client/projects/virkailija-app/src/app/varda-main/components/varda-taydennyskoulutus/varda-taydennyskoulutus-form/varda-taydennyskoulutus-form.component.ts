import { Component, OnInit, Input, Output, EventEmitter } from '@angular/core';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaVakajarjestajaUi } from 'projects/virkailija-app/src/app/utilities/models';
import { AuthService } from 'projects/virkailija-app/src/app/core/auth/auth.service';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { VardaTaydennyskoulutusDTO, VardaTaydennyskoulutusTyontekijaDTO, VardaTaydennyskoulutusTyontekijaListDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-taydennyskoulutus-dto.model';
import { FormGroup, FormControl, Validators } from '@angular/forms';
import { HenkilostoErrorMessageService, ErrorTree } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto-error-message.service';
import { Observable } from 'rxjs';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import * as moment from 'moment';
import { VardaFormValidators } from 'projects/virkailija-app/src/app/shared/validators/varda-form-validators';
import { VardaTaydennyskoulutusOsallistujaPickerComponent } from './taydennyskoulutus-osallistuja-picker/taydennyskoulutus-osallistuja-picker.component';
import { Lahdejarjestelma } from 'projects/virkailija-app/src/app/utilities/models/enums/hallinnointijarjestelma';
import { VardaDateService } from '../../../services/varda-date.service';

@Component({
  selector: 'app-varda-taydennyskoulutus-form',
  templateUrl: './varda-taydennyskoulutus-form.component.html',
  styleUrls: ['./varda-taydennyskoulutus-form.component.css', '../varda-taydennyskoulutus.component.css']
})
export class VardaTaydennyskoulutusFormComponent implements OnInit {
  @Input() taydennyskoulutus: VardaTaydennyskoulutusDTO;
  @Input() userAccess: UserAccess;
  @Output() refreshList = new EventEmitter<boolean>(true);
  currentOsallistujat: Array<VardaTaydennyskoulutusTyontekijaDTO>;
  tyontekijaList: Array<VardaTaydennyskoulutusTyontekijaListDTO>;
  i18n = VirkailijaTranslations;
  taydennyskoulutusForm: FormGroup;
  taydennyskoulutusFormErrors: Observable<Array<ErrorTree>>;
  isEdit: boolean;
  private henkilostoErrorService = new HenkilostoErrorMessageService();

  constructor(
    private authService: AuthService,
    private vakajarjestajaService: VardaVakajarjestajaService,
    private henkilostoService: VardaHenkilostoApiService
  ) {
    this.taydennyskoulutusFormErrors = this.henkilostoErrorService.initErrorList();
  }

  ngOnInit() {
    this.taydennyskoulutusForm = new FormGroup({
      id: new FormControl(this.taydennyskoulutus?.id),
      lahdejarjestelma: new FormControl(this.taydennyskoulutus?.lahdejarjestelma || Lahdejarjestelma.kayttoliittyma),
      nimi: new FormControl(this.taydennyskoulutus?.nimi, Validators.required),
      koulutuspaivia: new FormControl(this.taydennyskoulutus?.koulutuspaivia, [Validators.required, Validators.min(0.5), Validators.max(160), VardaFormValidators.remainderOf(0.5)]),
      suoritus_pvm: new FormControl(this.taydennyskoulutus ? moment(this.taydennyskoulutus?.suoritus_pvm, VardaDateService.vardaApiDateFormat) : null, Validators.required),
    });

    this.currentOsallistujat = [...this.taydennyskoulutus.taydennyskoulutus_tyontekijat];
   /*  this.listTyontekijat(); */
  }


  /* saveTaydennyskoulutus(form: FormGroup) {
    form.markAllAsTouched();
    this.henkilostoErrorService.resetErrorList();

    if (!form.valid) {
      Object.keys(form.controls).some(key => {
        if (form.controls[key]?.errors) {
          form.controls[key].setErrors({ ...form.controls[key].errors, scrollTo: true });
          return true;
        }
      });
    } else {
      const taydennyskoulutusJson: VardaTaydennyskoulutusDTO = {
        ...form.value,
        suoritus_pvm: form.value.suoritus_pvm.format(VardaDateService.vardaApiDateFormat)
      };

      if (this.taydennyskoulutus) {
        taydennyskoulutusJson.taydennyskoulutus_tyontekijat_add = [];

        this.henkilostoService.updateTaydennyskoulutus(taydennyskoulutusJson).subscribe({
          next: () => this.togglePanel(false, true),
          error: err => this.henkilostoErrorService.handleError(err)
        });
      } else {
        taydennyskoulutusJson.taydennyskoulutus_tyontekijat = [];

        this.henkilostoService.createTaydennyskoulutus(taydennyskoulutusJson).subscribe({
          next: () => this.togglePanel(false, true),
          error: err => this.henkilostoErrorService.handleError(err)
        });
      }

    }
  }

  deleteTaydennyskoulutus(): void {
    const taydennyskoulutusJson: VardaTaydennyskoulutusDTO = {
      ...this.taydennyskoulutusForm.value,
      suoritus_pvm: this.taydennyskoulutusForm.value.suoritus_pvm.format(VardaDateService.vardaApiDateFormat),
    };

  }

  closeTaydennyskoulutus(refresh: any) {

  }

  togglePanel(a, b?: any) {

  }

  disableForm() {
    this.isEdit = false;
    this.taydennyskoulutusForm.disable();
  }

  enableForm() {
    this.isEdit = true;
    this.taydennyskoulutusForm.enable();
  }


  selectOsallistujat(osallistujat: Array<VardaTaydennyskoulutusTyontekijaDTO>) {
    this.currentOsallistujat = osallistujat;
  }

  listTyontekijat() {
    const osallistujaJson = {
      vakajarjestaja_oid: this.vakajarjestajaService.getSelectedVakajarjestaja().organisaatio_oid
    };

    this.henkilostoService.getTaydennyskoulutuksetTyontekijat(osallistujaJson).subscribe(tyontekijaList => {
      tyontekijaList.forEach(tyontekija => tyontekija.nimi = `${tyontekija.henkilo_sukunimi}, ${tyontekija.henkilo_etunimet}`);
      this.tyontekijaList = tyontekijaList;
    });
  } */
}
