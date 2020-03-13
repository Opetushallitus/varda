import { Component, OnInit } from '@angular/core';
import { VardaApiWrapperService } from '../../../core/services/varda-api-wrapper.service';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { VardaUtilityService } from '../../../core/services/varda-utility.service';
import { VardaToimipaikkaDTO, VardaExtendedHenkiloModel, VardaHenkiloDTO, VardaLapsiDTO } from '../../../utilities/models';
import { of } from 'rxjs';
import { AuthService } from '../../../core/auth/auth.service';
import { LapsiByToimipaikkaDTO } from '../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { VardaToimipaikkaMinimalDto } from '../../../utilities/models/dto/varda-toimipaikka-dto.model';
import { UserAccess } from '../../../utilities/models/varda-user-access.model';

@Component({
  selector: 'app-varda-main-frame',
  templateUrl: './varda-main-frame.component.html',
  styleUrls: ['./varda-main-frame.component.css']
})
export class VardaMainFrameComponent implements OnInit {

  userAccess: UserAccess;
  toimipaikkaAccess: UserAccess;
  selectedToimipaikka: VardaToimipaikkaMinimalDto;
  toimipaikat: Array<VardaToimipaikkaMinimalDto>;
  henkilot: Array<VardaExtendedHenkiloModel>;

  ui: {
    isFetchingVarhaiskasvatussuhteet: boolean
  };

  constructor(
    private vardaApiWrapperService: VardaApiWrapperService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private authService: AuthService,
    private vardaUtilityService: VardaUtilityService) {
    this.ui = {
      isFetchingVarhaiskasvatussuhteet: false
    };

    this.vardaApiWrapperService.getAllToimipaikatForVakajarjestaja(this.vardaVakajarjestajaService.selectedVakajarjestaja.id).subscribe(
      (toimipaikat) => this.initToimipaikat(),
      (error) => console.error(error)
    );
  }

  onToimipaikkaChanged(data: any): void {
    if (!data) {
      return;
    }

    this.toimipaikkaAccess = this.authService.getUserAccess(data.organisaatio_oid)
    this.selectedToimipaikka = this.vardaVakajarjestajaService.getSelectedToimipaikka();
    this.getVarhaiskasvatussuhteetByToimipaikka();
  }

  onToimipaikkaUpdated(data: any): void {
    const toimipaikkaIndexToUpdate = this.toimipaikat.findIndex((toimipaikkaObj) => toimipaikkaObj.url === data.url);
    let isNew = false;
    if (this.toimipaikat[toimipaikkaIndexToUpdate]) {
      this.toimipaikat[toimipaikkaIndexToUpdate] = data;
    } else {
      isNew = true;
      this.toimipaikkaAccess = this.authService.getUserAccess(data.organisaatio_oid)
      this.toimipaikat.push(data);
    }

    this.selectedToimipaikka = this.vardaVakajarjestajaService.getSelectedToimipaikka();
    this.vardaVakajarjestajaService.setToimipaikat(this.toimipaikat, this.authService);

    if (isNew) {
      this.getVarhaiskasvatussuhteetByToimipaikka();
    }
  }

  getVarhaiskasvatussuhteetByToimipaikka(): void {
    this.ui.isFetchingVarhaiskasvatussuhteet = true;
    if (!this.vardaVakajarjestajaService.getSelectedToimipaikka()) {
      this.ui.isFetchingVarhaiskasvatussuhteet = false;
      return;
    }
    let selectedToimipaikka = this.vardaVakajarjestajaService.getSelectedToimipaikka();
    if (!selectedToimipaikka) {
      throw Error('No toimipaikka selected. Unable to fetch lapset for toimipaikka.');
    } else {
      if (!this.toimipaikat.includes(selectedToimipaikka))
        selectedToimipaikka = this.toimipaikat[0];
    }
    const toimipaikkaId = this.vardaUtilityService.parseIdFromUrl(selectedToimipaikka.url);
    this.vardaApiWrapperService.getAllLapsetForToimipaikka(toimipaikkaId)
      .subscribe({
        next: (lapset: Array<LapsiByToimipaikkaDTO>) => {
          // Filter duplicates since /toimipaikka/#/lapset api returns actually vakasuhde, not henkilo
          this.henkilot = lapset.filter((lapsi, index, self) => index === self.findIndex((otherLapsi) => (
            otherLapsi.henkilo_oid === lapsi.henkilo_oid && otherLapsi.lapsi_id === lapsi.lapsi_id
          ))).map(lapsi => {
            const henkiloExtendedDto = new VardaExtendedHenkiloModel();
            const henkiloDto = new VardaHenkiloDTO();
            const lapsiDto = new VardaLapsiDTO();
            henkiloDto.etunimet = lapsi.etunimet;
            henkiloDto.sukunimi = lapsi.sukunimi;
            henkiloDto.henkilo_oid = lapsi.henkilo_oid;
            henkiloDto.syntyma_pvm = lapsi.syntyma_pvm;
            henkiloDto.lapsi = [lapsi.lapsi_url];
            henkiloDto.url = lapsi.lapsi_url;
            henkiloDto.id = lapsi.lapsi_id;
            lapsiDto.oma_organisaatio_nimi = lapsi.oma_organisaatio_nimi;
            lapsiDto.paos_organisaatio_nimi = lapsi.paos_organisaatio_nimi;
            henkiloExtendedDto.henkilo = henkiloDto;
            henkiloExtendedDto.lapsi = lapsiDto;
            henkiloExtendedDto.isNew = false;
            return henkiloExtendedDto;
          });
          this.ui.isFetchingVarhaiskasvatussuhteet = false;
        },
        error: () => this.ui.isFetchingVarhaiskasvatussuhteet = false,
      });
  }

  updateToimipaikatAndVakasuhteet(): void {
    this.ui.isFetchingVarhaiskasvatussuhteet = true;
    of(null).subscribe(() => {
      this.getVarhaiskasvatussuhteetByToimipaikka();
    }, () => {
      this.ui.isFetchingVarhaiskasvatussuhteet = false;
    });
  }

  initToimipaikat(): void {
    this.toimipaikat = this.vardaVakajarjestajaService.getVakajarjestajaToimipaikat().katselijaToimipaikat
  }

  ngOnInit() {
    this.userAccess = this.authService.getUserAccess();

    setTimeout(() => {
      this.initToimipaikat();
    });
  }
}
