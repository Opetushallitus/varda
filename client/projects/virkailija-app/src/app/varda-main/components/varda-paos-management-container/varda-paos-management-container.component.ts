import { Component, OnInit, OnDestroy } from '@angular/core';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { Observable, Subscription } from 'rxjs';
import { PaosToimintaService } from './paos-toiminta.service';
import { AuthService } from '../../../core/auth/auth.service';
import { VardaKayttooikeusRoles, VardaVakajarjestajaUi } from '../../../utilities/models';
import { VirkailijaTranslations } from '../../../../assets/i18n/virkailija-translations.enum';

@Component({
  selector: 'app-varda-paos-management-container',
  templateUrl: './varda-paos-management-container.component.html',
  styleUrls: ['./varda-paos-management-container.component.css', './varda-paos-management-generic-styles.css']
})
export class VardaPaosManagementContainerComponent implements OnInit, OnDestroy {
  i18n = VirkailijaTranslations;
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  isVardaPaakayttaja: boolean;
  errorMessage$: Observable<string>;

  private vakajarjestajaSubscription: Subscription;

  constructor(
    private vakajarjestajaService: VardaVakajarjestajaService,
    private authService: AuthService,
    private paosToimintaService: PaosToimintaService
  ) { }

  ngOnInit() {
    this.isVardaPaakayttaja = this.authService.isCurrentUserSelectedVakajarjestajaRole(VardaKayttooikeusRoles.VARDA_PAAKAYTTAJA);
    this.errorMessage$ = this.paosToimintaService.errorMessage$;
    this.vakajarjestajaSubscription = this.vakajarjestajaService.listenSelectedVakajarjestaja()
      .subscribe({
        next: vakajarjestaja => this.selectedVakajarjestaja = vakajarjestaja,
        error: this.paosToimintaService.pushGenericErrorMessage,
      });
  }

  ngOnDestroy(): void {
    this.vakajarjestajaSubscription.unsubscribe();
  }

}
