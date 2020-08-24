import { Component, OnInit, OnDestroy, AfterViewInit } from '@angular/core';
import { VardaApiWrapperService } from '../../../core/services/varda-api-wrapper.service';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { VardaExtendedHenkiloModel, VardaHenkiloDTO, VardaLapsiDTO } from '../../../utilities/models';
import { AuthService } from '../../../core/auth/auth.service';
import { VardaToimipaikkaMinimalDto } from '../../../utilities/models/dto/varda-toimipaikka-dto.model';
import { UserAccess } from '../../../utilities/models/varda-user-access.model';
import { ModalEvent } from '../../../shared/components/varda-modal-form/varda-modal-form.component';
import { TyontekijaListDTO, } from '../../../utilities/models/dto/varda-tyontekija-dto.model';
import { LapsiListDTO } from '../../../utilities/models/dto/varda-lapsi-dto.model';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { Subscription } from 'rxjs';
import { VardaModalService } from '../../../core/services/varda-modal.service';

@Component({
  selector: 'app-varda-main-frame',
  templateUrl: './varda-main-frame.component.html',
  styleUrls: ['./varda-main-frame.component.css']
})
export class VardaMainFrameComponent implements OnInit, OnDestroy, AfterViewInit {
  i18n = VirkailijaTranslations;
  toimijaAccess: UserAccess;
  toimipaikkaAccess: UserAccess;
  selectedToimipaikka: VardaToimipaikkaMinimalDto;
  toimipaikat: Array<VardaToimipaikkaMinimalDto>;
  subscriptions: Array<Subscription> = [];
  activeSuhde: TyontekijaListDTO | LapsiListDTO;
  confirmedHenkiloFormLeave = true;

  constructor(
    private vardaApiWrapperService: VardaApiWrapperService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private authService: AuthService,
    private modalService: VardaModalService
  ) {

    this.vardaApiWrapperService.getAllToimipaikatForVakajarjestaja(this.vardaVakajarjestajaService.selectedVakajarjestaja.id).subscribe(
      (toimipaikat) => this.initToimipaikat(),
      (error) => console.error(error)
    );
  }

  onToimipaikkaChanged(toimipaikka: VardaToimipaikkaMinimalDto): void {
    this.toimipaikkaAccess = this.authService.getUserAccess(toimipaikka?.organisaatio_oid);
    this.selectedToimipaikka = toimipaikka;
  }

  initToimipaikat(): void {
    this.toimipaikat = this.vardaVakajarjestajaService.getVakajarjestajaToimipaikat().katselijaToimipaikat;
  }

  ngOnInit() {
    this.toimijaAccess = this.authService.getUserAccess();

    this.subscriptions.push(this.modalService.getModalOpen().subscribe(open => {
      if (!open) {
        this.activeSuhde = null;
      }
    }));
  }

  ngAfterViewInit() {
    this.initToimipaikat();
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
