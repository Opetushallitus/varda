import { Component, OnDestroy, OnInit } from '@angular/core';
import { NavigationEnd, Router, ActivatedRoute } from '@angular/router';
import { VardaVakajarjestajaService } from '../../../core/services/varda-vakajarjestaja.service';
import { VardaVakajarjestajaUi } from '../../../utilities/models';
import { UserAccess } from '../../../utilities/models/varda-user-access.model';
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
export class VardaHeaderComponent implements OnInit, OnDestroy {
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  userAccess: UserAccess;
  organisaatioUserAccess: UserAccess;
  vakajarjestajat: Array<VardaVakajarjestajaUi>;
  vakajarjestajaGroups: Array<{name?: string; className?: string; items: Array<VardaVakajarjestajaUi>}> = [];
  i18n = VirkailijaTranslations;
  toimipaikkaSelected: boolean;
  showRaportitBoolean: boolean;
  activeNavItem: string;
  subscriptions: Array<Subscription> = [];
  puutteellisetWarning: Observable<boolean>;

  constructor(
    private activatedRoute: ActivatedRoute,
    private router: Router,
    private vakajarjestajaService: VardaVakajarjestajaService,
    private raportitService: VardaRaportitService,
    private authService: AuthService,
    private dialog: MatDialog,
  ) { }

  ngOnInit() {
    this.selectedVakajarjestaja = this.vakajarjestajaService.getSelectedVakajarjestaja();

    this.subscriptions.push(
      this.router.events
        .pipe(filter(event => event instanceof NavigationEnd))
        .subscribe((navigationEnd) => {
          let topRoute = this.activatedRoute.firstChild;
          while (topRoute?.firstChild) {
            topRoute = topRoute.firstChild;
          }
          this.activeNavItem = topRoute.snapshot?.data?.nav_item || topRoute.snapshot.routeConfig.path;
        }),
      this.vakajarjestajaService.getVakajarjestajat()
        .pipe(filter(Boolean))
        .subscribe((vakajarjestajat: Array<VardaVakajarjestajaUi>) => {
          this.vakajarjestajat = vakajarjestajat;
          this.vakajarjestajat.sort((a, b) => a.nimi?.localeCompare(b.nimi, 'fi'));

          const activeVakajarjestajaList: Array<VardaVakajarjestajaUi> = [];
          const passiveVakajarjestajaList: Array<VardaVakajarjestajaUi> = [];
          this.vakajarjestajat.forEach(vakajarjestaja => {
            if (vakajarjestaja.active) {
              activeVakajarjestajaList.push(vakajarjestaja);
            } else {
              passiveVakajarjestajaList.push(vakajarjestaja);
            }
          });

          this.vakajarjestajaGroups = [];
          if (activeVakajarjestajaList.length > 0) {
            this.vakajarjestajaGroups.push({items: activeVakajarjestajaList});
          }
          if (passiveVakajarjestajaList.length > 0) {
            this.vakajarjestajaGroups.push({
              name: this.i18n.passive_plural,
              className: 'passive-vakajarjestaja-list',
              items: passiveVakajarjestajaList
            });
          }
        }),
      this.authService.permissionsChanged.subscribe(() => {
        this.userAccess = this.authService.anyUserAccess;
        this.organisaatioUserAccess = this.authService.organisaatioUserAccess;
        this.checkPuutteelliset();
      })
    );

    this.puutteellisetWarning = this.raportitService.showPuutteellisetError$;
  }

  changeVakajarjestaja(selectedVakajarjestaja: VardaVakajarjestajaUi): void {
    this.vakajarjestajaService.setSelectedVakajarjestaja(selectedVakajarjestaja);
    this.selectedVakajarjestaja = selectedVakajarjestaja;
  }

  checkPuutteelliset() {
    const puutteellisetWarningCookie = !!sessionStorage.getItem(VardaCookieEnum.puutteelliset_warning);

    this.showRaportitBoolean = this.organisaatioUserAccess.oph.katselija ||
      this.organisaatioUserAccess.raportit.katselija || this.organisaatioUserAccess.lapsitiedot.katselija ||
      this.organisaatioUserAccess.tyontekijatiedot.katselija || this.organisaatioUserAccess.huoltajatiedot.katselija;

    if (this.showRaportitBoolean) {
      this.subscriptions.push(
        this.raportitService.getPuutteellisetCount(this.selectedVakajarjestaja.id)
          .subscribe(showPuutteelliserError => {
            if (showPuutteelliserError && !puutteellisetWarningCookie) {
              this.dialog.open(PuutteellisetDialogComponent, { panelClass: 'puutteelliset-dialog' });
            }
          })
      );
    }
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe);
  }
}
