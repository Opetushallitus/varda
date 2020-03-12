import { Injectable } from '@angular/core';
import { Observable, Subject } from 'rxjs';
import { VardaApiService } from '../services/varda-api.service';
import { VardaVakajarjestajaService } from '../services/varda-vakajarjestaja.service';
import { NavigationEnd, Router } from '@angular/router';
import { VardaKayttajatyyppi, VardaKayttooikeusRoles, VardaToimipaikkaDTO } from '../../utilities/models';
import { HttpService } from 'varda-shared';
import { VardaToimipaikkaMinimalDto } from '../../utilities/models/dto/varda-toimipaikka-dto.model';
import { UserAccess, SaveAccess } from '../../utilities/models/varda-user-access.model';

class Kayttooikeus {
  kayttooikeus: VardaKayttooikeusRoles;
  organisaatio: string;
}

@Injectable()
export class AuthService {

  redirectUrl: string;
  loggedInUserAsiointikieli: string;
  loggedInUserAsiointikieliSubject = new Subject<string>();
  loggedInUserKayttooikeudet: Array<Kayttooikeus> = [];
  loggedInUserKayttooikeudetSubject = new Subject<any>();
  loggedInUserCurrentKayttooikeus: VardaKayttooikeusRoles;
  loggedInUserAfterAuthCheckUrl: string;
  selectedOrganisationLevelKayttooikeusRole: string;
  hasToimipaikkaLevelTallentajaRole: boolean;
  isAdminUser: boolean;

  loggedInUserVakajarjestajaLevelKayttooikeudet: Array<Kayttooikeus> = [];
  loggedInUserToimipaikkaLevelKayttooikeudet: Array<Kayttooikeus> = [];

  sessionInactivityTimeout: any = null;


  constructor(private vardaApiService: VardaApiService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private router: Router,
    private http: HttpService) {
    this.router.events.subscribe((s) => {
      if (s instanceof NavigationEnd) {
        const routeParts = s.url.split('?');
        const route = routeParts[0];
        this.loggedInUserAfterAuthCheckUrl = (route === '/') ? '/haku' : route;
        const currentKayttooikeusRole = this.loggedInUserCurrentKayttooikeus;
        if (route === '/' &&
          currentKayttooikeusRole &&
          currentKayttooikeusRole !== VardaKayttooikeusRoles.VARDA_TALLENTAJA) {
          this.router.navigate(['/haku']);
        }
      }
    });

    this.vardaVakajarjestajaService.getSelectedVakajarjestajaObs().subscribe((data) => {
      if (data.onVakajarjestajaChange) {
        this.initKayttooikeudet();
      }
    });
    this.isAdminUser = false;
  }

  initKayttooikeudet(): void {
    const selectedVakajarjestaja = this.vardaVakajarjestajaService.selectedVakajarjestaja;
    const selectedVakajarjestajaOrganisaatioOid = selectedVakajarjestaja.organisaatio_oid;
    this.loggedInUserVakajarjestajaLevelKayttooikeudet = [];
    this.loggedInUserToimipaikkaLevelKayttooikeudet = [];

    const selectedOrganisationLevelKayttooikeusRole = this.loggedInUserKayttooikeudet.filter((kayttooikeus) => {
      // Filter :: One user can have multiple permissions for one specific OrganisaatioOid
      return kayttooikeus.organisaatio === selectedVakajarjestajaOrganisaatioOid;
    });

    this.loggedInUserKayttooikeudet.forEach((kayttooikeus) => {
      const isVakajarjestajaOrganisation = this.findVakajarjestajaOrganisationByKayttooikeus(kayttooikeus);
      if (isVakajarjestajaOrganisation) {
        this.loggedInUserVakajarjestajaLevelKayttooikeudet.push(kayttooikeus);
      } else {
        this.loggedInUserToimipaikkaLevelKayttooikeudet.push(kayttooikeus);
      }
    });

    if (!selectedOrganisationLevelKayttooikeusRole) {
      this.loggedInUserCurrentKayttooikeus = VardaKayttooikeusRoles.VARDA_KATSELIJA;
    } else {
      const vardaTallentajaRole = selectedOrganisationLevelKayttooikeusRole.find((kayttooikeus) => {

        return kayttooikeus.kayttooikeus === VardaKayttooikeusRoles.VARDA_TALLENTAJA;
      });

      if (vardaTallentajaRole) {
        this.loggedInUserCurrentKayttooikeus = VardaKayttooikeusRoles.VARDA_TALLENTAJA;
      } else {
        this.loggedInUserCurrentKayttooikeus = VardaKayttooikeusRoles.VARDA_KATSELIJA;
      }
    }

    this.selectedOrganisationLevelKayttooikeusRole = this.loggedInUserCurrentKayttooikeus;

    const hasToimipaikkaLevelTallentajaRole = this.kayttooikeudetHasToimipaikkaLevelTallentajaRole();

    if (hasToimipaikkaLevelTallentajaRole || this.isAdminUser) {
      this.loggedInUserCurrentKayttooikeus = VardaKayttooikeusRoles.VARDA_TALLENTAJA;
      this.hasToimipaikkaLevelTallentajaRole = true;
    }

    if (this.loggedInUserCurrentKayttooikeus &&
      (this.loggedInUserCurrentKayttooikeus === VardaKayttooikeusRoles.VARDA_KATSELIJA)) {
      this.router.navigate([this.loggedInUserAfterAuthCheckUrl]);
    }

    setTimeout(() => {
      this.loggedInUserKayttooikeudetSubject.next(this.loggedInUserCurrentKayttooikeus);
    }, 1000);
  }

  /**
   * @deprecated Not working properly. getTallentajaToimipaikat() doesn't filter anything off. Returns always false.
   */
  private kayttooikeudetHasToimipaikkaLevelTallentajaRole(): boolean {
    let rv = false;
    const toimipaikkaLevelTallentajaRoles = this.loggedInUserToimipaikkaLevelKayttooikeudet.filter((kayttooikeus) => {
      const tallentajaRoolit = [VardaKayttooikeusRoles.VARDA_HUOLTAJA_TALLENTAJA, VardaKayttooikeusRoles.VARDA_TALLENTAJA]
      return tallentajaRoolit.includes(kayttooikeus.kayttooikeus)
    });

    if (toimipaikkaLevelTallentajaRoles && toimipaikkaLevelTallentajaRoles.length > 0) {
      const toimipaikatInSelectedVakajarjestaja = this.vardaVakajarjestajaService.getTallentajaToimipaikat();
      if (!toimipaikatInSelectedVakajarjestaja) {
        return rv;
      }
      toimipaikkaLevelTallentajaRoles.forEach((role) => {
        const foundInSelectedVakajarjestajaToimipaikat = toimipaikatInSelectedVakajarjestaja.find((toimipaikka: any) => {
          return toimipaikka.organisaatio_oid === role.organisaatio;
        });
        if (foundInSelectedVakajarjestajaToimipaikat) {
          // VardaToimipaikkaMinimalDto (toimipaikatInSelectedVakajarjestaja) doesn't have organisaatio_oid property so this is never reached
          rv = true;
          return;
        }
      });
    }

    return rv;
  }

  private findVakajarjestajaOrganisationByKayttooikeus(kayttooikeus: Kayttooikeus): any {
    return this.vardaVakajarjestajaService.vakaJarjestajat.find((vj) => {
      return kayttooikeus.organisaatio === vj.organisaatio_oid;
    });
  }

  getAuthorizedToimipaikat(toimipaikat: Array<VardaToimipaikkaMinimalDto>, hasSaveAccess?: SaveAccess): Array<VardaToimipaikkaMinimalDto> {
    return toimipaikat.filter((toimipaikka: VardaToimipaikkaDTO) => {
      const access = this.getUserAccess(toimipaikka.organisaatio_oid);
      if (!hasSaveAccess) {
        return (access.henkilostotiedot.katselija || access.huoltajatiedot.katselija || access.lapsitiedot.katselija)
      }
      else if (hasSaveAccess === SaveAccess.kaikki) {
        return (access.henkilostotiedot.tallentaja || access.huoltajatiedot.tallentaja || access.lapsitiedot.tallentaja)
      }
      else if (hasSaveAccess === SaveAccess.lapsitiedot) {
        return (access.huoltajatiedot.tallentaja || access.lapsitiedot.tallentaja)
      }
      else if (hasSaveAccess === SaveAccess.henkilostotiedot) {
        return (access.henkilostotiedot.tallentaja)
      }
      console.error("GetAuthorizedToimipaikat called with incorrect value", hasSaveAccess)
      return false
    })
  }

  loggedInUserAsiointikieliSet(): Observable<string> {
    return this.loggedInUserAsiointikieliSubject.asObservable();
  }

  casSessionExists(): Observable<any> {
    return this.vardaApiService.isLoggedInToCas();
  }

  getUserAsiointikieli(): string {
    return this.loggedInUserAsiointikieli;
  }

  setUserAsiointikieli(asiointikieli: string): void {
    this.loggedInUserAsiointikieli = asiointikieli;
    this.loggedInUserAsiointikieliSubject.next(asiointikieli);
  }

  getUserKayttooikeudet(): Array<any> {
    return this.loggedInUserKayttooikeudet;
  }

  precheckKayttajaTyyppi(kayttajaTyyppi: string): Observable<any> {
    return new Observable((precheckKayttajaTyyppiObserver) => {
      if (kayttajaTyyppi === VardaKayttajatyyppi.VIRKAILIJA) {
        // pass
      } else if (kayttajaTyyppi === VardaKayttajatyyppi.ADMIN) {
        this.isAdminUser = true;
      } else {
        precheckKayttajaTyyppiObserver.error({ isPalvelukayttaja: true });
        return;
      }
      precheckKayttajaTyyppiObserver.next();
      precheckKayttajaTyyppiObserver.complete();
    });
  }

  setUserKayttooikeudet(userKayttooikeusData: any): Observable<any> {
    return new Observable((setUserKayttooikeudetObserver) => {
      this.precheckKayttajaTyyppi(userKayttooikeusData.kayttajatyyppi).subscribe(() => {
        this.loggedInUserKayttooikeudet = userKayttooikeusData.kayttooikeudet;
        this.initKayttooikeudet();
        setUserKayttooikeudetObserver.next();
        setUserKayttooikeudetObserver.complete();
      }, (e) => {
        setUserKayttooikeudetObserver.error(e);
      });
    });
  }

  setSessionInactivityTimeout(): void {
    if (this.sessionInactivityTimeout) {
      clearTimeout(this.sessionInactivityTimeout);
    }
    this.sessionInactivityTimeout = setTimeout(() => {
      window.location.href = this.vardaApiService.getLogoutCasUrl();
    }, 3600000);
  }

  isCurrentUserSelectedVakajarjestajaRole(...roles: VardaKayttooikeusRoles[]): boolean {
    // Admin-user has TALLENTAJA-permissions on VakaJarjestaja-level
    if (this.isAdminUser && (roles.includes(VardaKayttooikeusRoles.VARDA_TALLENTAJA)
      || roles.includes(VardaKayttooikeusRoles.VARDA_HUOLTAJA_TALLENTAJA))) {
      return true;
    }

    const selectedVakajarjestaja = this.vardaVakajarjestajaService.selectedVakajarjestaja.organisaatio_oid;
    return this.loggedInUserVakajarjestajaLevelKayttooikeudet
      .filter(kayttooikeus => kayttooikeus.organisaatio === selectedVakajarjestaja)
      .some(kayttooikeus => roles.indexOf(kayttooikeus.kayttooikeus) !== -1);
  }

  isCurrentUserToimipaikkaRole(oid: string, ...roles: VardaKayttooikeusRoles[]): boolean {
    return this.loggedInUserToimipaikkaLevelKayttooikeudet
      .filter(kayttooikeus => kayttooikeus.organisaatio === oid)
      .some(kayttooikeus => roles.indexOf(kayttooikeus.kayttooikeus) !== -1);
  }

  /* Katselija is an user who can't modify vakatieto in given toimipaikka. This considers only vaka roles in following cases:
  * Toimija katselija = toimipaikka katselija
  * Toimija katselija + toimipaikka tallentaja != toimipaikka katselija
  * Toimija tallentaja = never katselija
  * Toimipaikka tallentaja = never katselija
  pääkäyttäjä = katselija from this point of view
   */
  isCurrentUserKatselijaForToimipaikka(oid: string): boolean {
    return !this.isCurrentUserToimipaikkaRole(oid, VardaKayttooikeusRoles.VARDA_TALLENTAJA)
      && !this.isCurrentUserSelectedVakajarjestajaRole(VardaKayttooikeusRoles.VARDA_TALLENTAJA)
      && (this.isCurrentUserToimipaikkaRole(oid, VardaKayttooikeusRoles.VARDA_KATSELIJA, VardaKayttooikeusRoles.VARDA_PAAKAYTTAJA)
        || this.isCurrentUserSelectedVakajarjestajaRole(VardaKayttooikeusRoles.VARDA_KATSELIJA, VardaKayttooikeusRoles.VARDA_PAAKAYTTAJA)
      );
  }


  getUserAccess(toimipaikkaOid?: string): UserAccess {
    const getRoles = (...roles: Array<VardaKayttooikeusRoles>): boolean => {
      const toimipaikkaRole = !!(toimipaikkaOid && this.isCurrentUserToimipaikkaRole(toimipaikkaOid, ...roles))
      return this.isCurrentUserSelectedVakajarjestajaRole(...roles) || toimipaikkaRole
    }

    const access: UserAccess = {
      paakayttaja: getRoles(VardaKayttooikeusRoles.VARDA_PAAKAYTTAJA),
      lapsitiedot: {
        katselija: getRoles(VardaKayttooikeusRoles.VARDA_TALLENTAJA, VardaKayttooikeusRoles.VARDA_KATSELIJA),
        tallentaja: getRoles(VardaKayttooikeusRoles.VARDA_TALLENTAJA)
      },
      huoltajatiedot: {
        katselija: getRoles(VardaKayttooikeusRoles.VARDA_HUOLTAJA_TALLENTAJA, VardaKayttooikeusRoles.VARDA_HUOLTAJA_KATSELIJA),
        tallentaja: getRoles(VardaKayttooikeusRoles.VARDA_HUOLTAJA_TALLENTAJA)
      },
      henkilostotiedot: {
        katselija: false,
        tallentaja: false
      },
      tilapainen_henkilosto: {
        katselija: false,
        tallentaja: false
      },
      taydennyskoulutustiedot: {
        katselija: false,
        tallentaja: false
      }
    };

    return access;
  }

  getUserAccessIfAnyToimipaikka(toimipaikat: Array<VardaToimipaikkaMinimalDto>): UserAccess {
    const userAccess = this.getUserAccess();
    toimipaikat.forEach((toimipaikka: VardaToimipaikkaMinimalDto) => {
      const toimipaikkaAccess = this.getUserAccess(toimipaikka.organisaatio_oid)
      userAccess.paakayttaja = userAccess.paakayttaja || toimipaikkaAccess.paakayttaja
      Object.keys(toimipaikkaAccess).filter((key: string) => key !== 'paakayttaja').forEach((key: string) => {
        userAccess[key].katselija = userAccess[key].katselija || toimipaikkaAccess[key].katselija
        userAccess[key].tallentaja = userAccess[key].tallentaja || toimipaikkaAccess[key].tallentaja
      })
    })
    return userAccess
  }

}
