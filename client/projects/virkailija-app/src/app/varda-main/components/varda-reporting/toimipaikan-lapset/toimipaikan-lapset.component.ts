import { Component, Input, OnChanges, ViewChild } from '@angular/core';
import { VardaApiService } from '../../../../core/services/varda-api.service';
import { ToimipaikanLapsi } from '../../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { VardaUtilityService } from '../../../../core/services/varda-utility.service';
import { UserAccess } from '../../../../utilities/models/varda-user-access.model';

@Component({
  selector: 'app-toimipaikan-lapset',
  templateUrl: './toimipaikan-lapset.component.html',
  styleUrls: ['./toimipaikan-lapset.component.css']
})
export class ToimipaikanLapsetComponent implements OnChanges {
  @Input() selectedToimipaikanLapsi: ToimipaikanLapsi;
  @Input() userAccess: UserAccess;
  @ViewChild('toimipaikanLapsetScrollTo') toimipaikanLapsetScrollTo: any;
  constructor(private vardaApiService: VardaApiService, private vardaUtilityService: VardaUtilityService) { }

  ngOnChanges() {
    this.selectedToimipaikanLapsi.henkilo = {
      etunimet: '',
      kutsumanimi: '',
      sukunimi: '',
      id: null,
      henkilo_oid: '',
      syntyma_pvm: '',
    };
    this.selectedToimipaikanLapsi.varhaiskasvatuspaatokset = [];
    this.selectedToimipaikanLapsi.varhaiskasvatussuhteet = [];
    this.selectedToimipaikanLapsi.maksutiedot = [];
    this.fetchToimipaikanLapsi(this.selectedToimipaikanLapsi);
  }

  fetchToimipaikanLapsi({ paos_organisaatio_nimi, oma_organisaatio_nimi }): void {
    this.vardaApiService.getLapsiKooste(this.selectedToimipaikanLapsi.lapsi_id).subscribe((data) => {
      this.selectedToimipaikanLapsi = { ...data, paos_organisaatio_nimi: paos_organisaatio_nimi, oma_organisaatio_nimi: oma_organisaatio_nimi };
      this.toimipaikanLapsetScrollTo.nativeElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  getVakasuhteetForVakapaatos(id: number) {
    return this.selectedToimipaikanLapsi.varhaiskasvatussuhteet.filter(vakasuhde => {
      return String(id) === this.vardaUtilityService.parseIdFromUrl(vakasuhde.varhaiskasvatuspaatos);
    });
  }
}
