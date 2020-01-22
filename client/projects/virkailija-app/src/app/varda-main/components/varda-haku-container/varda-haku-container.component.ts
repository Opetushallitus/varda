import {Component, OnInit} from '@angular/core';
import {HenkilohakuResultDTO, HenkilohakuSearchDTO, HenkilohakuType, FilterStatus, FilterObject} from '../../../utilities/models/dto/varda-henkilohaku-dto.model';
import {VardaApiService} from '../../../core/services/varda-api.service';
import {VardaVakajarjestajaService} from '../../../core/services/varda-vakajarjestaja.service';
import {VardaErrorMessageService} from '../../../core/services/varda-error-message.service';
import {TranslateService} from '@ngx-translate/core';

@Component({
  selector: 'app-varda-haku-container',
  templateUrl: './varda-haku-container.component.html',
  styleUrls: ['./varda-haku-container.component.css']
})
export class VardaHakuContainerComponent implements OnInit {
  searchResult: Array<HenkilohakuResultDTO>;
  lastSearchDto: HenkilohakuSearchDTO;
  vakajarjestajaId: number;
  ui: {
    formSaveErrors: Array<{ key: string, msg: string, }>;
    formSaveErrorMsg: string;
    isLoading: boolean,
  };
  nextSearchLink: string;

  constructor(private vardaApiService: VardaApiService,
              private vardaVakajarjestajaService: VardaVakajarjestajaService,
              private vardaErrorMessageService: VardaErrorMessageService,
              private translate: TranslateService) {
    this.searchResult = [];
    this.lastSearchDto = {
      search: '',
      type: HenkilohakuType.lapset,
      filter_status: FilterStatus.voimassaOlevat,
      filter_object: FilterObject.vakapaatokset
    };
    this.ui = {
      isLoading: false,
      formSaveErrorMsg: null,
      formSaveErrors: [],
    };
    this.nextSearchLink = null;
  }

  ngOnInit() {
    this.vakajarjestajaId = Number(this.vardaVakajarjestajaService.selectedVakajarjestaja.id);
  }

  // If no searchDto we search more.
  search(searchDto?: HenkilohakuSearchDTO) {
    this.ui.isLoading = true;
    if (searchDto) {
      this.nextSearchLink = null;
      this.lastSearchDto.search = searchDto.search;
      this.lastSearchDto.type = searchDto.type || this.lastSearchDto.type;
      this.lastSearchDto.filter_status = searchDto.filter_status || this.lastSearchDto.filter_status;
      this.lastSearchDto.filter_object = searchDto.filter_object || this.lastSearchDto.filter_object;
    }
    this.vardaApiService.getHenkilohaku(this.vakajarjestajaId, this.lastSearchDto, this.nextSearchLink)
      .subscribe({
        next: searchresult => {
          this.searchResult = !searchDto
            ? [...this.searchResult, ...searchresult.results]
            : searchresult.results;
          this.nextSearchLink = searchresult.next;
          this.ui.isLoading = false;
          this.clearErrors();
        },
        error: () => {
          this.translate.get('alert.haku.generic-error').subscribe(hakuErrorMessage => {
            this.ui.isLoading = false;
            this.ui.formSaveErrorMsg = hakuErrorMessage;
          });
        },
      });
  }

  searchMore() {
    this.search();
  }

  clearErrors() {
    this.ui.formSaveErrors = [];
    this.ui.formSaveErrorMsg = null;
  }
}
