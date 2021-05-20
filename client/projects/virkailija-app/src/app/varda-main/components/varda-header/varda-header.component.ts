import { Component, Input, OnChanges, OnDestroy, SimpleChanges } from '@angular/core';
import { NavigationEnd, Router, ActivatedRoute } from '@angular/router';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { VardaVakajarjestajaUi } from '../../../utilities/models';
import { UserAccess, UserAccessKeys } from '../../../utilities/models/varda-user-access.model';
import { filter } from 'rxjs/operators';
import { VirkailijaTranslations } from 'projects/virkailija-app/src/assets/i18n/virkailija-translations.enum';
import { AuthService } from '../../../core/auth/auth.service';
import { Observable, Subscription } from 'rxjs';
import { MatDialog } from '@angular/material/dialog';
import { PuutteellisetDialogComponent } from '../varda-raportit/varda-puutteelliset-tiedot/puutteelliset-dialog/puutteelliset-dialog.component';
import { VardaRaportitService } from '../../../core/services/varda-raportit.service';
import { VardaCookieEnum } from '../../../utilities/models/enums/varda-cookie.enum';


@Component({
  selector: 'app-varda-header',
  templateUrl: './varda-header.component.html',
  styleUrls: ['./varda-header.component.css']
})
export class VardaHeaderComponent implements OnChanges, OnDestroy {
  @Input() selectedVakajarjestaja: VardaVakajarjestajaUi;
  @Input() toimipaikkaAccessToAnyToimipaikka: UserAccess;
  tilapainenHenkilostoOnly: boolean;
  vakajarjestajat: Array<VardaVakajarjestajaUi>;
  i18n = VirkailijaTranslations;
  toimipaikkaSelected: boolean;
  showRaportitBoolean: boolean;
  activeNavItem: string;
  subscriptions: Array<Subscription> = [];
  puutteellisetWarning: Observable<boolean>;


  constructor(
    private activatedRoute: ActivatedRoute,
    private router: Router,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private raportitService: VardaRaportitService,
    private authService: AuthService,
    private dialog: MatDialog,
  ) {

    this.tilapainenHenkilostoOnly = this.authService.hasAccessOnlyTo([UserAccessKeys.tilapainenHenkilosto], true);

    this.subscriptions.push(
      this.router.events.pipe(filter(event => event instanceof NavigationEnd)).subscribe((navigationEnd) => {
        let topRoute = this.activatedRoute.firstChild;
        while (topRoute?.firstChild) {
          topRoute = topRoute.firstChild;
        }

        this.activeNavItem = topRoute.snapshot?.data?.nav_item || topRoute.snapshot.routeConfig.path;
      })
    );


    this.vardaVakajarjestajaService.getVakajarjestajat().pipe(filter(Boolean)).subscribe((vakajarjestajat: Array<VardaVakajarjestajaUi>) => {
      this.vakajarjestajat = vakajarjestajat;
      this.vakajarjestajat.sort((a, b) => a.nimi?.localeCompare(b.nimi, 'fi'));
    });

    this.puutteellisetWarning = this.raportitService.showPuutteellisetError$;
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes.selectedVakajarjestaja) {
      this.checkPuutteelliset();
    }
  }

  changeVakajarjestaja(selectedVakajarjestaja: VardaVakajarjestajaUi): void {
    this.vardaVakajarjestajaService.setSelectedVakajarjestaja(selectedVakajarjestaja);
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe);
  }

  checkPuutteelliset() {
    const toimijaAccess = this.authService.getUserAccess();
    const puutteellisetWarningCookie = !!sessionStorage.getItem(VardaCookieEnum.puutteelliset_warning);

    this.showRaportitBoolean = toimijaAccess.oph.katselija
      || toimijaAccess.raportit.katselija
      || toimijaAccess.lapsitiedot.katselija
      || toimijaAccess.tyontekijatiedot.katselija
      || toimijaAccess.huoltajatiedot.katselija;

    if (this.showRaportitBoolean) {
      this.subscriptions.push(
        this.raportitService.getPuutteellisetCount(this.selectedVakajarjestaja.id).subscribe(showPuutteelliserError => {
          if (showPuutteelliserError && !puutteellisetWarningCookie) {
            this.dialog.open(PuutteellisetDialogComponent, { panelClass: 'puutteelliset-dialog' });
          }
        })
      );
    }


  }

}
