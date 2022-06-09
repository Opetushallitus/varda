import { Component, Input, OnDestroy, OnInit, ViewChild } from '@angular/core';
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
import { VardaUtilityService } from '../../../../core/services/varda-utility.service';
import { Subscription } from 'rxjs';
import { VardaShowMoreLessComponent } from '../../../../shared/components/varda-show-more-less/varda-show-more-less.component';
import { ModelNameEnum } from '../../../../utilities/models/enums/model-name.enum';

interface NumberOfDisplayed {
  kielipainotus: number;
  toiminnallinenpainotus: number;
}

@Component({
  selector: 'app-toimipaikka-painotukset',
  templateUrl: './toimipaikka-painotukset.component.html',
  styleUrls: ['./toimipaikka-painotukset.component.css', '../varda-toimipaikka-form.component.css']
})
export class ToimipaikkaPainotuksetComponent implements OnInit, OnDestroy {
  @ViewChild('showMoreLessKielipainotus') showMoreLessComponentKielipainotus: VardaShowMoreLessComponent;
  @ViewChild('showMoreLessToiminnallinenPainotus') showMoreLessComponentToiminnallinenPainotus: VardaShowMoreLessComponent;
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

  private subscriptions: Array<Subscription> = [];

  constructor(
    private snackBarService: VardaSnackBarService,
    private vakajarjestajaApiService: VardaVakajarjestajaApiService,
    private utilityService: VardaUtilityService
  ) { }

  ngOnInit() {
    const activeToimipaikka = this.vakajarjestajaApiService.activeToimipaikka.getValue();
    if (activeToimipaikka) {
      this.kielipainotusList = activeToimipaikka.kielipainotukset.sort(sortByAlkamisPvm);
      this.toiminnallinenPainotusList = activeToimipaikka.toiminnalliset_painotukset.sort(sortByAlkamisPvm);
    }

    this.subscriptions.push(
      this.utilityService.getFocusObjectSubject().subscribe(focusObject => {
        if (focusObject?.type === ModelNameEnum.TOIMINNALLINEN_PAINOTUS && this.toiminnallinenPainotusList) {
          this.showUntil(ModelNameEnum.TOIMINNALLINEN_PAINOTUS,
            this.toiminnallinenPainotusList.findIndex(object => object.id === focusObject.id));
        } else if (focusObject?.type === ModelNameEnum.KIELIPAINOTUS && this.kielipainotusList) {
          this.showUntil(ModelNameEnum.KIELIPAINOTUS,
            this.kielipainotusList.findIndex(object => object.id === focusObject.id));
        }
      })
    );
  }

  addKielipainotus(kielipainotus: KielipainotusDTO) {
    this.kielipainotusList = this.kielipainotusList.filter(obj => obj.id !== kielipainotus.id);
    this.kielipainotusList.push(kielipainotus);
    this.kielipainotusList = this.kielipainotusList.sort(sortByAlkamisPvm);
    this.updateActiveToimipaikka();
    this.utilityService.setFocusObjectSubject({type: ModelNameEnum.KIELIPAINOTUS, id: kielipainotus.id});
  }

  deleteKielipainotus(objectId: number) {
    this.kielipainotusList = this.kielipainotusList.filter(obj => obj.id !== objectId);
    this.updateActiveToimipaikka();
    this.utilityService.setFocusObjectSubject(null);
  }

  addToiminnallinenPainotus(toiminnallinenPainotus: ToiminnallinenPainotusDTO) {
    this.toiminnallinenPainotusList = this.toiminnallinenPainotusList.filter(obj => obj.id !== toiminnallinenPainotus.id);
    this.toiminnallinenPainotusList.push(toiminnallinenPainotus);
    this.toiminnallinenPainotusList = this.toiminnallinenPainotusList.sort(sortByAlkamisPvm);
    this.updateActiveToimipaikka();
    this.utilityService.setFocusObjectSubject({type: ModelNameEnum.TOIMINNALLINEN_PAINOTUS, id: toiminnallinenPainotus.id});
  }

  deleteToiminnallinenPainotus(objectId: number) {
    this.toiminnallinenPainotusList = this.toiminnallinenPainotusList.filter(obj => obj.id !== objectId);
    this.updateActiveToimipaikka();
    this.utilityService.setFocusObjectSubject(null);
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

  showUntil(type: ModelNameEnum, index: number) {
    const numberOfDisplayed = this.numberOfDisplayed[type];
    const showMoreLessComponent = type === ModelNameEnum.KIELIPAINOTUS ? this.showMoreLessComponentKielipainotus :
      this.showMoreLessComponentToiminnallinenPainotus;
    if (index !== -1 && numberOfDisplayed < index + 1) {
      showMoreLessComponent?.showMore();
      setTimeout(() => this.showUntil(type, index), 100);
    }
  }

  ngOnDestroy() {
    this.subscriptions.forEach(subscription => subscription.unsubscribe());
  }
}
