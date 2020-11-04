import { Component, OnInit, OnDestroy } from '@angular/core';
import { VardaExtendedHenkiloModel } from '../../../utilities/models';
import { AuthService } from '../../../core/auth/auth.service';
import { VardaToimipaikkaMinimalDto } from '../../../utilities/models/dto/varda-toimipaikka-dto.model';
import { UserAccess } from '../../../utilities/models/varda-user-access.model';
import { ModalEvent } from '../../../shared/components/varda-modal-form/varda-modal-form.component';
import { TyontekijaListDTO, } from '../../../utilities/models/dto/varda-tyontekija-dto.model';
import { LapsiListDTO } from '../../../utilities/models/dto/varda-lapsi-dto.model';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { Subscription } from 'rxjs';
import { VardaModalService } from '../../../core/services/varda-modal.service';

export interface ToimipaikkaChange {
  toimipaikka: VardaToimipaikkaMinimalDto;
  toimipaikat: Array<VardaToimipaikkaMinimalDto>;
}

@Component({
  selector: 'app-varda-main-frame',
  templateUrl: './varda-main-frame.component.html',
  styleUrls: ['./varda-main-frame.component.css']
})
export class VardaMainFrameComponent implements OnInit, OnDestroy {
  i18n = VirkailijaTranslations;
  toimijaAccess: UserAccess;
  toimipaikkaAccess: UserAccess;
  selectedToimipaikka: VardaToimipaikkaMinimalDto;
  toimipaikat: Array<VardaToimipaikkaMinimalDto>;
  subscriptions: Array<Subscription> = [];
  activeSuhde: TyontekijaListDTO | LapsiListDTO;
  confirmedHenkiloFormLeave = true;

  constructor(
    private authService: AuthService,
    private modalService: VardaModalService
  ) { }

  onToimipaikkaChanged(toimipaikkaChange: ToimipaikkaChange): void {
    this.toimipaikkaAccess = this.authService.getUserAccess(toimipaikkaChange.toimipaikka?.organisaatio_oid);
    this.selectedToimipaikka = toimipaikkaChange.toimipaikka;
    this.toimipaikat = toimipaikkaChange.toimipaikat;
  }

  ngOnInit() {
    this.toimijaAccess = this.authService.getUserAccess();

    this.subscriptions.push(this.modalService.getModalOpen().subscribe(open => {
      if (!open) {
        this.activeSuhde = null;
      }
    }));
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  handleFormClose($event: ModalEvent) {
    if ($event === ModalEvent.hidden) {
      this.activeSuhde = null;
      this.confirmedHenkiloFormLeave = true;
    }
  }

  henkiloFormValuesChanged(hasChanged: boolean): void {
    this.confirmedHenkiloFormLeave = !hasChanged;
  }

  onHenkiloAdded(extendedHenkilo: VardaExtendedHenkiloModel): void {
    this.confirmedHenkiloFormLeave = true;
    this.activeSuhde = null;
  }

  openHenkilo(suhde: LapsiListDTO | TyontekijaListDTO): void {
    this.activeSuhde = suhde;
  }
}
