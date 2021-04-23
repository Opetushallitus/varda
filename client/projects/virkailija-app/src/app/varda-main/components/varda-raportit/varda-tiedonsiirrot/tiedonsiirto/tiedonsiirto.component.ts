import { Component, OnChanges } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { MatTableDataSource } from '@angular/material/table';
import { ActivatedRoute, Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { AuthService } from 'projects/virkailija-app/src/app/core/auth/auth.service';
import { VardaRaportitService } from 'projects/virkailija-app/src/app/core/services/varda-raportit.service';
import { VardaSnackBarService } from 'projects/virkailija-app/src/app/core/services/varda-snackbar.service';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { VardaTiedonsiirtoDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tiedonsiirto-dto.model';
import { Observable } from 'rxjs';
import { KoodistoDTO, KoodistoEnum, VardaKoodistoService } from 'varda-shared';
import { AbstractTiedonsiirrotSectionsComponent, TiedonsiirrotColumnFields, TiedonsiirrotSearchFilter } from '../tiedonsiirrot-sections.abstract';
import { TiedonsiirtoDialogComponent, TiedonsiirtoDialogData } from '../tiedonsiirto-dialog/tiedonsiirto-dialog.component';
import * as moment from 'moment';


@Component({
  selector: 'app-varda-tiedonsiirto',
  templateUrl: './tiedonsiirto.component.html',
  styleUrls: [
    './tiedonsiirto.component.css',
    '../varda-tiedonsiirrot.component.css',
    '../../varda-raportit.component.css'
  ]
})
export class VardaTiedonsiirtoComponent extends AbstractTiedonsiirrotSectionsComponent implements OnChanges {
  tiedonsiirrot: MatTableDataSource<VardaTiedonsiirtoDTO>;
  expandResponse = false;
  lahdejarjestelmaKoodisto: Observable<KoodistoDTO>;

  columnFields: Array<TiedonsiirrotColumnFields> = [
    { key: 'timestamp', name: this.i18n.tiedonsiirrot_aikaleima, selected: true },
    { key: 'json', name: this.i18n.tiedonsiirrot_json, selected: true },
    { key: 'target', name: this.i18n.tiedonsiirrot_kayttaja, selected: true },
    { key: 'request_method', name: this.i18n.tiedonsiirrot_tyyppi, selected: true },
    { key: 'request_url', name: this.i18n.tiedonsiirrot_rajapinta, selected: true },
    { key: 'error', name: this.i18n.tiedonsiirrot_syy, selected: true },
    { key: 'username', name: this.i18n.tiedonsiirrot_kayttaja, selected: true },
    { key: 'lahdejarjestelma', name: this.i18n.lahdejarjestelma, selected: true },
  ];

  searchFilter: TiedonsiirrotSearchFilter = {
    ...this.searchFilter,
    timestamp_after: moment(),
    timestamp_before: moment(),
  };

  constructor(
    private dialog: MatDialog,
    private snackBarService: VardaSnackBarService,
    private router: Router,
    private koodistoService: VardaKoodistoService,
    protected authService: AuthService,
    protected translateService: TranslateService,
    protected route: ActivatedRoute,
    protected vakajarjestajaService: VardaVakajarjestajaService,
    protected raportitService: VardaRaportitService,
  ) {
    super(authService, translateService, route, vakajarjestajaService, raportitService);

    const path = this.router.url.split('?').shift().split('/').pop();

    this.searchFilter.successful = path === 'onnistuneet';


    if (this.searchFilter.successful) {
      this.columnFields.find(field => field.key === 'error').selected = false;
      this.columnFields.find(field => field.key === 'error').disabled = true;
      this.toggleColumn();
    }

    this.lahdejarjestelmaKoodisto = this.koodistoService.getKoodisto(KoodistoEnum.lahdejarjestelma);
  }

  ngOnChanges() {
    if (this.tiedonsiirrot) {
      this.getPage();
    }
  }

  getPage(firstPage?: boolean) {
    this.tiedonsiirrot = null;
    this.isLoading.next(true);

    if (firstPage) {
      this.searchFilter.cursor = null;
      this.searchFilter.reverse = false;
    }

    this.raportitService.getTiedonsiirrot(this.getSearchFilter()).subscribe({
      next: tiedonsiirrotData => {
        this.parseCursors(tiedonsiirrotData);
        this.tiedonsiirrot = this.mapTiedonsiirrot(tiedonsiirrotData.results);
      },
      error: (err) => this.errorService.handleError(err, this.snackBarService)
    }).add(() => setTimeout(() => this.isLoading.next(false), 500));
  }

  openJSON(tiedonsiirto: VardaTiedonsiirtoDTO) {
    const tiedonsiirtoData: TiedonsiirtoDialogData = {
      tiedonsiirto: tiedonsiirto
    };
    const dialogRef = this.dialog.open(TiedonsiirtoDialogComponent, { data: tiedonsiirtoData });
  }

  mapTiedonsiirrot(results: Array<VardaTiedonsiirtoDTO>): MatTableDataSource<VardaTiedonsiirtoDTO> {
    const tiedonsiirrot = results.map(tiedonsiirto => {
      const jsonResponse: JSON = tiedonsiirto.response_body ? JSON.parse(tiedonsiirto.response_body) : {};
      tiedonsiirto.response_list = [];
      Object.entries(jsonResponse).forEach(([key, value]) => {
        if (Array.isArray(value)) {
          value?.forEach(error => tiedonsiirto.response_list.push({ field: key, error_code: error.error_code, expand: this.expandResponse }));
        }
      });

      return tiedonsiirto;
    });

    return new MatTableDataSource(tiedonsiirrot);
  }

  toggleReasonsExpand() {
    this.expandResponse = !this.expandResponse;
    this.tiedonsiirrot.data.forEach(tiedonsiirto => tiedonsiirto.response_list.forEach(response => response.expand = this.expandResponse));
  }
}
