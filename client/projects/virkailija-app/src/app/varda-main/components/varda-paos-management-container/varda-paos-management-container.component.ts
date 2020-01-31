import { Component, OnInit, OnDestroy } from '@angular/core';
import { Title } from "@angular/platform-browser";
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { Observable, Subscription } from 'rxjs';
import { VardaVakajarjestaja } from '../../../utilities/models/varda-vakajarjestaja.model';
import { LoadingHttpService } from 'varda-shared';
import { PaosToimintaService } from './paos-toiminta.service';
import { TranslateService } from '@ngx-translate/core';
import { AuthService } from '../../../core/auth/auth.service';
import { VardaKayttooikeusRoles } from '../../../utilities/models';

@Component({
  selector: 'app-varda-paos-management-container',
  templateUrl: './varda-paos-management-container.component.html',
  styleUrls: ['./varda-paos-management-container.component.css', './varda-paos-management-generic-styles.css']
})
export class VardaPaosManagementContainerComponent implements OnInit, OnDestroy {
  selectedVakajarjestaja: VardaVakajarjestaja;
  isVakajarjestajaKunta: boolean;
  isVardaPaakayttaja: boolean;
  errorMessage$: Observable<string>;

  private vakajarjestajaSubscription: Subscription;

  constructor(private vakajarjestajaService: VardaVakajarjestajaService,
    private loadingHttpService: LoadingHttpService,
    private authService: AuthService,
    private titleService: Title,
    private translate: TranslateService,
    private paosToimintaService: PaosToimintaService) { }

  ngOnInit() {
    this.translate.get('label.paos-management.topic').subscribe(title =>
      this.titleService.setTitle(`${title} - Varda`)
    );
    this.isVardaPaakayttaja = this.authService.isCurrentUserSelectedVakajarjestajaRole(VardaKayttooikeusRoles.VARDA_PAAKAYTTAJA)
    this.selectedVakajarjestaja = new VardaVakajarjestaja();
    this.errorMessage$ = this.paosToimintaService.errorMessage$;
    this.vakajarjestajaSubscription = this.vakajarjestajaService.getSelectedVakajarjestajaObs()
      .subscribe({
        next: (vakajarjestajaObsResult) => {
          const vakajarjestaja: VardaVakajarjestaja = vakajarjestajaObsResult.vakajarjestaja;
          this.selectedVakajarjestaja = vakajarjestaja;
          this.isVakajarjestajaKunta = vakajarjestaja && vakajarjestaja.kunnallinen_kytkin;
        },
        error: this.paosToimintaService.pushGenericErrorMessage,
      });


  }

  isLoading() {
    return this.loadingHttpService.isLoading();
  }

  ngOnDestroy(): void {
    /* TODO: CSCVARDA-1491 -- poista kun title käytössä muuallakin */
    this.titleService.setTitle(`Varda`);
    this.vakajarjestajaSubscription.unsubscribe();
  }

}
