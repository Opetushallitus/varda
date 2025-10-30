import { Component, OnDestroy, OnInit, ViewEncapsulation } from '@angular/core';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { Observable, Subscription } from 'rxjs';
import { PaosToimintaService } from './paos-toiminta.service';
import { AuthService } from '../../../core/auth/auth.service';
import { VardaVakajarjestajaUi } from '../../../utilities/models';
import { VirkailijaTranslations } from '../../../../assets/i18n/virkailija-translations.enum';

@Component({
  selector: 'app-varda-paos-management-container',
  templateUrl: './varda-paos-management-container.component.html',
  styleUrls: ['./varda-paos-management-container.component.css', './varda-paos-management-generic-styles.css'],
  encapsulation: ViewEncapsulation.None
})
export class VardaPaosManagementContainerComponent implements OnInit, OnDestroy {
  i18n = VirkailijaTranslations;
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  isVardaPaakayttaja: boolean;
  isAdminUser: boolean;
  errorMessage$: Observable<string>;

  private vakajarjestajaSubscription: Subscription;

  constructor(
    private vakajarjestajaService: VardaVakajarjestajaService,
    private authService: AuthService,
    private paosToimintaService: PaosToimintaService
  ) { }

  ngOnInit() {
    this.isVardaPaakayttaja = this.authService.anyUserAccess.paakayttaja;
    this.isAdminUser = this.authService.isAdminUser;
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
