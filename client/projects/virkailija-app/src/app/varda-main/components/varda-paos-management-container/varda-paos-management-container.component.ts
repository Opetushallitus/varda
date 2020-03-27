import { Component, OnInit, OnDestroy } from '@angular/core';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { Observable, Subscription } from 'rxjs';
import { VardaVakajarjestaja } from '../../../utilities/models/varda-vakajarjestaja.model';
import { LoadingHttpService } from 'varda-shared';
import { PaosToimintaService } from './paos-toiminta.service';
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
    private paosToimintaService: PaosToimintaService) { }

  ngOnInit() {
    this.isVardaPaakayttaja = this.authService.isCurrentUserSelectedVakajarjestajaRole(VardaKayttooikeusRoles.VARDA_PAAKAYTTAJA);
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

  ngOnDestroy(): void {
    this.vakajarjestajaSubscription.unsubscribe();
  }

}
