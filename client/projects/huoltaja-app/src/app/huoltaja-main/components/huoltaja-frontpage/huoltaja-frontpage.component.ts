import { Component, OnInit } from '@angular/core';

import { HuoltajanLapsiDTO } from '../../../utilities/models/dto/huoltajan-lapsi-dto';
import { HuoltajaApiService } from '../../../services/huoltaja-api.service';
import { LoginService, LoadingHttpService } from 'varda-shared';
import { VarhaiskasvatussuhdeDTO } from '../../../utilities/models/dto/varhaiskasvatussuhde-dto';
import { HuoltajaFrontpageLapsiComponent } from './huoltaja-frontpage-lapsi/huoltaja-frontpage-lapsi.component';

@Component({
  selector: 'app-huoltaja-frontpage',
  templateUrl: './huoltaja-frontpage.component.html',
  styleUrls: ['./huoltaja-frontpage.component.css']
})
export class HuoltajaFrontpageComponent implements OnInit {
  loadingHttpService: LoadingHttpService;
  lapsi: HuoltajanLapsiDTO;
  fetchError: boolean;

  constructor(private apiService: HuoltajaApiService,
    private loginService: LoginService) {
    this.apiService.getHuoltajanLapsi(loginService.currentUserInfo.henkilo_oid).subscribe((data: HuoltajanLapsiDTO) => {
      this.lapsi = data;
    }, (error: any) => {
      console.error(error.message);
      this.fetchError = true;
    });
  }

  onkoVakasuhdeVoimassa(vakasuhde: VarhaiskasvatussuhdeDTO): boolean {
    const today = new Date();
    return !(vakasuhde.paattymis_pvm < today.toISOString());
  }

  isLoading() {
    return this.loadingHttpService.isLoading();
  }

  ngOnInit() { }
}
