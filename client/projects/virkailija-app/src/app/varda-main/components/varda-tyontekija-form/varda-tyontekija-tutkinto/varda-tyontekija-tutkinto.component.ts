import { Component, OnChanges, Input, Output, EventEmitter } from '@angular/core';
import { VardaHenkiloDTO } from 'projects/virkailija-app/src/app/utilities/models';
import { UserAccess } from 'projects/virkailija-app/src/app/utilities/models/varda-user-access.model';
import { VardaTutkintoDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tutkinto-dto.model';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { VardaHenkilostoApiService } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto.service';
import { BehaviorSubject, forkJoin, Observable } from 'rxjs';
import { FormGroup, FormControl, Validators } from '@angular/forms';
import { HenkilostoErrorMessageService, ErrorTree } from 'projects/virkailija-app/src/app/core/services/varda-henkilosto-error-message.service';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { VardaKoodistoService } from 'varda-shared';
import { KoodistoEnum, KoodistoSortBy, KoodistoDTO, CodeDTO } from 'projects/varda-shared/src/lib/dto/koodisto-models';
import { VardaToimipaikkaMinimalDto } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';



@Component({
  selector: 'app-varda-tyontekija-tutkinto',
  templateUrl: './varda-tyontekija-tutkinto.component.html',
  styleUrls: ['./varda-tyontekija-tutkinto.component.css', '../varda-tyontekija-form.component.css']
})
export class VardaTyontekijaTutkintoComponent implements OnChanges {
  @Input() toimipaikkaAccess: UserAccess;
  @Input() henkilo: VardaHenkiloDTO;
  @Input() henkilonToimipaikka: VardaToimipaikkaMinimalDto;
  @Output() changeTutkinnot = new EventEmitter<Array<VardaTutkintoDTO>>(true);
  tutkintoFormErrors: Observable<Array<ErrorTree>>;
  private henkilostoErrorService = new HenkilostoErrorMessageService();
  i18n = VirkailijaTranslations;
  tutkintoViewLimit = 3;
  tutkintoOptions: Array<CodeDTO>;
  uusiTutkinto: any;
  henkilonTutkinnot: BehaviorSubject<Array<VardaTutkintoDTO>> = new BehaviorSubject<Array<VardaTutkintoDTO>>([]);
  henkilonTutkinnotExpand: boolean;
  addTutkinto: boolean;

  tutkintoForm: FormGroup;

  constructor(
    private henkilostoService: VardaHenkilostoApiService,
    private koodistoService: VardaKoodistoService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService
  ) {
    this.tutkintoFormErrors = this.henkilostoErrorService.initErrorList();
    this.henkilonTutkinnot.subscribe(tutkinnot => {
      this.changeTutkinnot.emit(tutkinnot);
    });
  }

  ngOnChanges() {
    if (this.toimipaikkaAccess.tyontekijatiedot.katselija) {
      this.getHenkilonTutkinnot();
    }
  }

  getHenkilonTutkinnot() {
    this.henkilostoErrorService.resetErrorList();
    this.initTutkintoForm();
    forkJoin([
      this.koodistoService.getKoodisto(KoodistoEnum.tutkinto, KoodistoSortBy.codeValue),
      this.henkilostoService.getTutkinnot(this.henkilo.henkilo_oid)
    ]).subscribe({
      next: ([tutkintoKoodisto, henkilonTutkinnot]) => {
        if (henkilonTutkinnot && tutkintoKoodisto) {
          this.tutkintoOptions = tutkintoKoodisto.codes.filter(koodisto => !henkilonTutkinnot.some(tutkinto => tutkinto.tutkinto_koodi === koodisto.code_value)).reverse();
          this.henkilonTutkinnot.next(this.fillTutkinnot(henkilonTutkinnot, tutkintoKoodisto));
          this.addTutkinto = !henkilonTutkinnot.length;
        }
      },
      error: err => this.henkilostoErrorService.handleError(err)
    });
  }

  fillTutkinnot(henkilonTutkinnot: Array<VardaTutkintoDTO>, tutkintoKoodisto: KoodistoDTO) {
    const existingTutkinnot = henkilonTutkinnot.map(henkilonTutkinto => {
      const foundKoodisto = tutkintoKoodisto.codes.find(tutkinto => tutkinto.code_value === henkilonTutkinto.tutkinto_koodi);
      return {
        ...henkilonTutkinto,
        tutkinto_koodi: foundKoodisto.code_value,
        tutkinto_nimi: foundKoodisto.name
      };
    });

    return existingTutkinnot;
  }

  createTutkinto(tutkintoFormGroup: FormGroup) {
    if (tutkintoFormGroup.valid) {
      this.henkilostoService.createTutkinto(tutkintoFormGroup.value).subscribe({
        next: () => this.getHenkilonTutkinnot(),
        error: err => this.henkilostoErrorService.handleError(err, tutkintoFormGroup)
      });
    }
  }

  deleteTutkinto(tutkintoId: number) {
    this.henkilostoService.deleteTutkinto(tutkintoId).subscribe({
      next: data => this.getHenkilonTutkinnot(),
      error: err => this.henkilostoErrorService.handleError(err)
    });
  }


  initTutkintoForm() {
    this.tutkintoForm = new FormGroup({
      henkilo_oid: new FormControl(this.henkilo.henkilo_oid),
      toimipaikka_oid: new FormControl(this.henkilonToimipaikka?.organisaatio_oid),
      vakajarjestaja_oid: new FormControl(this.vardaVakajarjestajaService.getSelectedVakajarjestaja().organisaatio_oid),
      tutkinto_koodi: new FormControl(null, Validators.required)
    });
  }

}
