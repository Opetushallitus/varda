import { Component, Input, OnInit } from '@angular/core';
import { VardaErrorMessageService } from 'projects/virkailija-app/src/app/core/services/varda-error-message.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaVakajarjestajaApiService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja-api.service';
import {
  KielipainotusDTO,
  ToiminnallinenPainotusDTO,
  ToimipaikkaKooste
} from 'projects/virkailija-app/src/app/utilities/models/dto/varda-toimipaikka-dto.model';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { CodeDTO } from 'varda-shared';
import { sortByAlkamisPvm } from '../../../../utilities/helper-functions';

interface NumberOfDisplayed {
  kielipainotus: number;
  toiminnallinenpainotus: number;
}

@Component({
  selector: 'app-toimipaikka-painotukset',
  templateUrl: './toimipaikka-painotukset.component.html',
  styleUrls: ['./toimipaikka-painotukset.component.css', '../varda-toimipaikka-form.component.css']
})
export class ToimipaikkaPainotuksetComponent implements OnInit {
  @Input() toimipaikka: ToimipaikkaKooste;
  @Input() kielikoodisto: Array<CodeDTO>;
  @Input() saveAccess: boolean;
  @Input() isEdit: boolean;
  @Input() errorService: VardaErrorMessageService;
  @Input() minStartDate: Date;
  @Input() maxEndDate: Date;

  i18n = VirkailijaTranslations;
  kielipainotusList: Array<KielipainotusDTO> = [];
  toiminnallinenPainotusList: Array<ToiminnallinenPainotusDTO> = [];
  addKielipainotusBoolean: boolean;
  addToimintapainotusBoolean: boolean;
  numberOfDisplayed: NumberOfDisplayed = {kielipainotus: 0, toiminnallinenpainotus: 0};

  constructor(
    private snackBarService: VardaSnackBarService,
    private vakajarjestajaApiService: VardaVakajarjestajaApiService
  ) { }

  ngOnInit() {
    const activeToimipaikka = this.vakajarjestajaApiService.activeToimipaikka.getValue();
    if (activeToimipaikka) {
      this.kielipainotusList = activeToimipaikka.kielipainotukset.sort(sortByAlkamisPvm);
      this.toiminnallinenPainotusList = activeToimipaikka.toiminnalliset_painotukset.sort(sortByAlkamisPvm);
    }
  }

  addKielipainotus(kielipainotus: KielipainotusDTO) {
    this.kielipainotusList = this.kielipainotusList.filter(obj => obj.id !== kielipainotus.id);
    this.kielipainotusList.push(kielipainotus);
    this.kielipainotusList = this.kielipainotusList.sort(sortByAlkamisPvm);
    this.updateActiveToimipaikka();
  }

  deleteKielipainotus(objectId: number) {
    this.kielipainotusList = this.kielipainotusList.filter(obj => obj.id !== objectId);
    this.updateActiveToimipaikka();
  }

  addToiminnallinenPainotus(toiminnallinenPainotus: ToiminnallinenPainotusDTO) {
    this.toiminnallinenPainotusList = this.toiminnallinenPainotusList.filter(obj => obj.id !== toiminnallinenPainotus.id);
    this.toiminnallinenPainotusList.push(toiminnallinenPainotus);
    this.toiminnallinenPainotusList = this.toiminnallinenPainotusList.sort(sortByAlkamisPvm);
    this.updateActiveToimipaikka();
  }

  deleteToiminnallinenPainotus(objectId: number) {
    this.toiminnallinenPainotusList = this.toiminnallinenPainotusList.filter(obj => obj.id !== objectId);
    this.updateActiveToimipaikka();
  }

  updateActiveToimipaikka() {
    const activeToimipaikka = this.vakajarjestajaApiService.activeToimipaikka.getValue();
    activeToimipaikka.kielipainotukset = this.kielipainotusList;
    activeToimipaikka.toiminnalliset_painotukset = this.toiminnallinenPainotusList;
    this.vakajarjestajaApiService.activeToimipaikka.next(activeToimipaikka);
  }

  hideAddKielipainotus() {
    this.addKielipainotusBoolean = false;
  }

  hideAddToiminnallinenPainotus() {
    this.addToimintapainotusBoolean = false;
  }
}
