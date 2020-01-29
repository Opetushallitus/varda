import {Component, EventEmitter, Input, OnChanges, Output, ViewChild} from '@angular/core';
import {VardaApiService} from '../../../../core/services/varda-api.service';
import {ToimipaikanLapsi} from '../../../../utilities/models/dto/varda-henkilohaku-dto.model';

@Component({
  selector: 'app-toimipaikan-lapset',
  templateUrl: './toimipaikan-lapset.component.html',
  styleUrls: ['./toimipaikan-lapset.component.css']
})
export class ToimipaikanLapsetComponent implements OnChanges {

  @Input() selectedToimipaikanLapsi: ToimipaikanLapsi;
  @Output() uiLoading: EventEmitter<boolean>;
  @ViewChild('toimipaikanLapsetScrollTo') toimipaikanLapsetScrollTo: any;
  constructor(private vardaApiService: VardaApiService) {
    this.uiLoading = new EventEmitter<boolean>(true);
  }

  ngOnChanges() {
    this.selectedToimipaikanLapsi.henkilo = {
      etunimet: '',
      kutsumanimi: '',
      sukunimi: '',
      id: 0,
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
      this.toimipaikanLapsetScrollTo.nativeElement.scrollIntoView({behavior: 'smooth'})
    });
  }
}
