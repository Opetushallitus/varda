import { Component } from '@angular/core';
import { MatTableDataSource } from '@angular/material/table';
import { ActivatedRoute } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { AuthService } from 'projects/virkailija-app/src/app/core/auth/auth.service';
import { VardaRaportitService } from 'projects/virkailija-app/src/app/core/services/varda-raportit.service';
import { VardaVakajarjestajaService } from 'projects/virkailija-app/src/app/core/services/varda-vakajarjestaja.service';
import { VardaTiedonsiirtoYhteenvetoDTO } from 'projects/virkailija-app/src/app/utilities/models/dto/varda-tiedonsiirto-dto.model';
import { AbstractTiedonsiirrotSectionsComponent } from '../tiedonsiirrot-sections.abstract';


@Component({
  selector: 'app-varda-tiedonsiirrot-yhteenveto',
  templateUrl: './tiedonsiirrot-yhteenveto.component.html',
  styleUrls: [
    './tiedonsiirrot-yhteenveto.component.css',
    '../varda-tiedonsiirrot.component.css',
    '../../varda-raportit.component.css'
  ]
})
export class VardaTiedonsiirrotYhteenvetoComponent extends AbstractTiedonsiirrotSectionsComponent {
  yhteenvedot: MatTableDataSource<VardaTiedonsiirtoYhteenvetoDTO>;


  columnFields = [
    { key: 'date', name: this.i18n.tiedonsiirrot_yhteenveto_date },
    { key: 'successful', name: this.i18n.tiedonsiirrot_yhteenveto_successful },
    { key: 'unsuccessful', name: this.i18n.tiedonsiirrot_yhteenveto_unsuccessful },
    { key: 'total', name: this.i18n.tiedonsiirrot_yhteenveto_unsuccessful },
    { key: 'username', name: this.i18n.tiedonsiirrot_kayttaja },
  ];

  constructor(
    protected authService: AuthService,
    protected translateService: TranslateService,
    protected route: ActivatedRoute,
    protected vakajarjestajaService: VardaVakajarjestajaService,
    protected raportitService: VardaRaportitService,
  ) {
    super(authService, translateService, route, vakajarjestajaService, raportitService);
  }

  getPage(firstPage?: boolean) {
    this.yhteenvedot = null;
    this.isLoading.next(true);

    if (firstPage) {
      this.searchFilter.cursor = null;
      this.searchFilter.reverse = false;
    }

    this.raportitService.getTiedonsiirrotYhteenveto(this.getSearchFilter()).subscribe({
      next: yhteenvetoData => {
        this.parseCursors(yhteenvetoData);
        this.yhteenvedot = new MatTableDataSource(yhteenvetoData.results);
      },
      error: (err) => this.errorService.handleError(err)
    }).add(() => setTimeout(() => this.isLoading.next(false), 500));
  }

}
