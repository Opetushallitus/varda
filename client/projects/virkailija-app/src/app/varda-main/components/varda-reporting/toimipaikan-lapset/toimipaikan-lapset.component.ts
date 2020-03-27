import { Component, Input, OnChanges, ViewChild } from '@angular/core';
import { VardaApiService } from '../../../../core/services/varda-api.service';
import { ToimipaikanLapsi } from '../../../../utilities/models/dto/varda-henkilohaku-dto.model';

@Component({
  selector: 'app-toimipaikan-lapset',
  templateUrl: './toimipaikan-lapset.component.html',
  styleUrls: ['./toimipaikan-lapset.component.css']
})
export class ToimipaikanLapsetComponent implements OnChanges {

  @Input() selectedToimipaikanLapsi: ToimipaikanLapsi;
  @ViewChild('toimipaikanLapsetScrollTo') toimipaikanLapsetScrollTo: any;
  constructor(private vardaApiService: VardaApiService) { }

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
    this.fetchToimipaikanLapsi();
  }

  fetchToimipaikanLapsi(): void {

    this.vardaApiService.getLapsiKooste(this.selectedToimipaikanLapsi.lapsi_id).subscribe((data) => {
      this.selectedToimipaikanLapsi = data;
      this.toimipaikanLapsetScrollTo.nativeElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }
}
