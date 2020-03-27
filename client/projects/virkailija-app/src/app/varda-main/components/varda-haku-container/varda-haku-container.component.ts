import { Component, OnInit } from '@angular/core';
import { HenkilohakuResultDTO, HenkilohakuSearchDTO, HenkilohakuType, FilterStatus, FilterObject } from '../../../utilities/models/dto/varda-henkilohaku-dto.model';
import { VardaApiService } from '../../../core/services/varda-api.service';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { TranslateService } from '@ngx-translate/core';
import { VardaPageDto } from '../../../utilities/models/dto/varda-page-dto';
import { AuthService } from '../../../core/auth/auth.service';
import { UserAccess } from '../../../utilities/models/varda-user-access.model';

export interface HakuAccess {
  userAccess: UserAccess;
  showLapset: boolean;
  showHenkilosto: boolean;
  isTallentaja: boolean;
}

@Component({
  selector: 'app-varda-haku-container',
  templateUrl: './varda-haku-container.component.html',
  styleUrls: ['./varda-haku-container.component.css']
})
export class VardaHakuContainerComponent implements OnInit {
  searchResult: VardaPageDto<HenkilohakuResultDTO>;
  lastSearchDto: HenkilohakuSearchDTO;
  vakajarjestajaId: number;
  access: HakuAccess;
  ui: {
    formSaveErrors: Array<{ key: string, msg: string, }>;
    formSaveErrorMsg: string;
  };
  nextSearchLink: string;
  prevSearchLink: string;

  constructor(private vardaApiService: VardaApiService,
    private authService: AuthService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private translate: TranslateService) {
    this.searchResult = null;
    this.lastSearchDto = {
      search: '',
      type: HenkilohakuType.lapset,
      filter_status: FilterStatus.voimassaOlevat,
      filter_object: FilterObject.vakapaatokset
    };
    this.ui = {
      formSaveErrorMsg: null,
      formSaveErrors: [],
    };
    this.nextSearchLink = null;
    this.prevSearchLink = null;
    this.initUserAccess();
  }

  ngOnInit() {
    this.vakajarjestajaId = Number(this.vardaVakajarjestajaService.selectedVakajarjestaja.id);
  }

  // If no searchDto we search more.
  search(searchDto?: HenkilohakuSearchDTO, previous?: boolean) {
    if (searchDto) {
      this.nextSearchLink = null;
      this.prevSearchLink = null;
      this.lastSearchDto.search = searchDto.search;
      this.lastSearchDto.type = searchDto.type || this.lastSearchDto.type;
      this.lastSearchDto.filter_status = searchDto.filter_status || this.lastSearchDto.filter_status;
      this.lastSearchDto.filter_object = searchDto.filter_object || this.lastSearchDto.filter_object;
    }
    const searchLink = previous ? this.prevSearchLink : this.nextSearchLink;
    this.vardaApiService.getHenkilohaku(this.vakajarjestajaId, this.lastSearchDto, searchLink)
      .subscribe({
        next: searchresult => {
          const henkilohakuResults = searchresult.results;
          henkilohakuResults.forEach(henkiloHakuResult => henkiloHakuResult.henkilo.lapsi = [henkiloHakuResult.url]);
          this.searchResult = searchresult;
          this.prevSearchLink = searchresult.previous;
          this.nextSearchLink = searchresult.next;
          this.clearErrors();
        },
        error: () => {
          this.translate.get('alert.haku.generic-error').subscribe(hakuErrorMessage => {
            this.ui.formSaveErrorMsg = hakuErrorMessage;
          });
        }
      });
  }

  clearErrors() {
    this.ui.formSaveErrors = [];
    this.ui.formSaveErrorMsg = null;
  }

  initUserAccess(): void {
    const userAccess = this.authService.getUserAccessIfAnyToimipaikka(this.vardaVakajarjestajaService.getVakajarjestajaToimipaikat().katselijaToimipaikat);

    this.access = {
      userAccess: userAccess,
      showLapset: userAccess.huoltajatiedot.katselija || userAccess.lapsitiedot.katselija,
      showHenkilosto: userAccess.henkilostotiedot.katselija || userAccess.taydennyskoulutustiedot.katselija,
      isTallentaja: Object.keys(userAccess).some(key => userAccess[key].tallentaja)
    };

    if (this.access.showLapset) {
      this.lastSearchDto.type = HenkilohakuType.lapset;
      if (!this.access.userAccess.lapsitiedot.katselija) {
        this.lastSearchDto.filter_object = FilterObject.maksutiedot;
      }
    } else if (this.access.showHenkilosto) {
      this.lastSearchDto.type = HenkilohakuType.tyontekija;
    }
  }
}
