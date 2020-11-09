import { Injectable } from '@angular/core';
import { BehaviorSubject, combineLatest, Observable, Subject } from 'rxjs';
import { VardaApiService } from '../services/varda-api.service';
import { VardaVakajarjestajaService } from '../services/varda-vakajarjestaja.service';
import { NavigationEnd, Router } from '@angular/router';
import { VardaKayttajatyyppi, VardaKayttooikeusRoles, VardaToimipaikkaDTO } from '../../utilities/models';
import { VardaToimipaikkaMinimalDto } from '../../utilities/models/dto/varda-toimipaikka-dto.model';
import { SaveAccess, UserAccess, UserAccessKeys } from '../../utilities/models/varda-user-access.model';
import { environment } from 'projects/huoltaja-app/src/environments/environment';
import { filter } from 'rxjs/operators';

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
  loggedInUserAfterAuthCheckUrl: string;
  selectedOrganisationLevelKayttooikeusRole: string;
  hasToimipaikkaLevelTallentajaRole: boolean;
  isAdminUser: boolean;
  isOPHUser: boolean;

  loggedInUserVakajarjestajaLevelKayttooikeudet: Array<Kayttooikeus> = [];
  loggedInUserToimipaikkaLevelKayttooikeudet: Array<Kayttooikeus> = [];

  sessionInactivityTimeout: any = null;

  toimipaikkaAccessToAnyToimipaikka$ = new BehaviorSubject<UserAccess>(null);

  constructor(private vardaApiService: VardaApiService,
    private vardaVakajarjestajaService: VardaVakajarjestajaService,
    private router: Router) {

    combineLatest([
      (router.events).pipe(filter(event => event instanceof NavigationEnd)),
      this.toimipaikkaAccessToAnyToimipaikka$.asObservable()
    ]).subscribe(([navigation, toimipaikkaAccessToAny]) => {
      if (navigation instanceof NavigationEnd && toimipaikkaAccessToAny) {
        const route = navigation.url.split('?').shift();

        const tempHenkilostoOnlyRoutes = ['/vakatoimija', '/tilapainen-henkilosto'];
        if (this.isTilapainenHenkilostoOnly() && !tempHenkilostoOnlyRoutes.includes(route)) {
          this.router.navigate(['/tilapainen-henkilosto']);
        }
      }
    });

    this.vardaVakajarjestajaService.getTallentajaToimipaikatObs().subscribe((data) => {
      this.initUserAccess(data);
    });

    this.isAdminUser = false;
  }

  initUserAccess(toimipaikat: Array<VardaToimipaikkaMinimalDto>): void {
    const selectedVakajarjestaja = this.vardaVakajarjestajaService.selectedVakajarjestaja;
    this.loggedInUserVakajarjestajaLevelKayttooikeudet = this.loggedInUserKayttooikeudet.filter(kayttooikeus => kayttooikeus.organisaatio === selectedVakajarjestaja.organisaatio_oid);
    this.loggedInUserToimipaikkaLevelKayttooikeudet = this.loggedInUserKayttooikeudet.filter(
      kayttooikeus => toimipaikat.some(toimipaikka => toimipaikka.organisaatio_oid === kayttooikeus.organisaatio)
    );

    const toimipaikkaAccessIfAny = this.getUserAccessIfAnyToimipaikka(toimipaikat);
    this.toimipaikkaAccessToAnyToimipaikka$.next(toimipaikkaAccessIfAny);

    const routeParts = this.router.url.split('?');
    // these parts are just for simply printing your user access in the selected organization
    const userAccessToConsole = {
      [selectedVakajarjestaja.nimi]: this.loggedInUserVakajarjestajaLevelKayttooikeudet.map(kayttooikeus => kayttooikeus.kayttooikeus),
      toimipaikat: {}
    };

    this.loggedInUserToimipaikkaLevelKayttooikeudet.forEach(kayttooikeus => {
      const toimipaikka = toimipaikat.find(toimipaikkaDto => toimipaikkaDto.organisaatio_oid === kayttooikeus.organisaatio);
      const key = `${toimipaikka.nimi}_${toimipaikka.organisaatio_oid}`;
      userAccessToConsole.toimipaikat[key] = userAccessToConsole.toimipaikat[key] || [];
      userAccessToConsole.toimipaikat[key].push(kayttooikeus.kayttooikeus);
    });
    if (environment.production) {
      setTimeout(() => console.log('USER ACCESS / KÄYTTÖOIKEUDET', JSON.stringify(userAccessToConsole, null, '\t')), 2000);
    } else {
      console.log('USER ACCESS / KÄYTTÖOIKEUDET', userAccessToConsole);
    }

  }


  getToimipaikkaAccessToAnyToimipaikka(): Observable<UserAccess> {
    return this.toimipaikkaAccessToAnyToimipaikka$.asObservable();
  }

  getAuthorizedToimipaikat(toimipaikat: Array<VardaToimipaikkaMinimalDto>, hasSaveAccess?: SaveAccess): Array<VardaToimipaikkaMinimalDto> {
    return toimipaikat.filter((toimipaikka: VardaToimipaikkaMinimalDto) => {
      const access = this.getUserAccess(toimipaikka.organisaatio_oid);
      if (!hasSaveAccess) {
        return (access.tyontekijatiedot.katselija || access.taydennyskoulutustiedot.katselija || access.huoltajatiedot.katselija || access.lapsitiedot.katselija);
      } else if (hasSaveAccess === SaveAccess.kaikki) {
        return (access.tyontekijatiedot.tallentaja || access.taydennyskoulutustiedot.tallentaja || access.huoltajatiedot.tallentaja || access.lapsitiedot.tallentaja);
      } else if (hasSaveAccess === SaveAccess.lapsitiedot) {
        return (access.huoltajatiedot.tallentaja || access.lapsitiedot.tallentaja);
      } else if (hasSaveAccess === SaveAccess.henkilostotiedot) {
        return (access.tyontekijatiedot.tallentaja || access.taydennyskoulutustiedot.tallentaja);
      } else if (hasSaveAccess === SaveAccess.tyontekijatiedot) {
        return (access.tyontekijatiedot.tallentaja);
      }
      console.error('GetAuthorizedToimipaikat called with incorrect value', hasSaveAccess);
      return false;
    });
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
        this.isOPHUser = true;
      } else if (kayttajaTyyppi === VardaKayttajatyyppi.OPH_STAFF) {
        this.isOPHUser = true;
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
        setUserKayttooikeudetObserver.next();
        setUserKayttooikeudetObserver.complete();
      }, (e) => {
        setUserKayttooikeudetObserver.error(e);
      });
    });
  }

  setSessionInactivityTimeout(): void {
    if (window.location.hostname !== 'localhost') {
      if (this.sessionInactivityTimeout) {
        clearTimeout(this.sessionInactivityTimeout);
      }
      this.sessionInactivityTimeout = setTimeout(() => window.location.href = this.vardaApiService.getLogoutCasUrl(), 3600000);
    }
  }

  isCurrentUserSelectedVakajarjestajaRole(...roles: VardaKayttooikeusRoles[]): boolean {
    // Admin-user has TALLENTAJA-permissions on VakaJarjestaja-level
    if (this.isAdminUser && !roles.includes(VardaKayttooikeusRoles.VARDA_PAAKAYTTAJA)) {
      return true;
    }

    const selectedVakajarjestaja = this.vardaVakajarjestajaService.getSelectedVakajarjestaja().organisaatio_oid;
    return this.loggedInUserVakajarjestajaLevelKayttooikeudet
      .filter(kayttooikeus => kayttooikeus.organisaatio === selectedVakajarjestaja)
      .some(kayttooikeus => roles.indexOf(kayttooikeus.kayttooikeus) !== -1);
  }

  isCurrentUserToimipaikkaRole(oid: string, ...roles: VardaKayttooikeusRoles[]): boolean {
    return this.loggedInUserToimipaikkaLevelKayttooikeudet
      .filter(kayttooikeus => kayttooikeus.organisaatio === oid)
      .some(kayttooikeus => roles.indexOf(kayttooikeus.kayttooikeus) !== -1);
  }

  getUserAccess(toimipaikkaOID?: string): UserAccess {
    const getRoles = (...roles: Array<VardaKayttooikeusRoles>): boolean => {
      const toimipaikkaRole = !!(toimipaikkaOID && this.isCurrentUserToimipaikkaRole(toimipaikkaOID, ...roles));
      return this.isCurrentUserSelectedVakajarjestajaRole(...roles) || toimipaikkaRole;
    };

    const toimipaikka = toimipaikkaOID ? this.vardaVakajarjestajaService.getToimipaikkaAsMinimal(toimipaikkaOID) : null;

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
      tyontekijatiedot: {
        katselija: getRoles(VardaKayttooikeusRoles.HENKILOSTO_TYONTEKIJA_TALLENTAJA, VardaKayttooikeusRoles.HENKILOSTO_TYONTEKIJA_KATSELIJA),
        tallentaja: getRoles(VardaKayttooikeusRoles.HENKILOSTO_TYONTEKIJA_TALLENTAJA)
      },
      tilapainenHenkilosto: {
        katselija: getRoles(VardaKayttooikeusRoles.HENKILOSTO_TILAPAISET_TALLENTAJA, VardaKayttooikeusRoles.HENKILOSTO_TILAPAISET_KATSELIJA),
        tallentaja: getRoles(VardaKayttooikeusRoles.HENKILOSTO_TILAPAISET_TALLENTAJA)
      },
      taydennyskoulutustiedot: {
        katselija: getRoles(VardaKayttooikeusRoles.HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA, VardaKayttooikeusRoles.HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA),
        tallentaja: getRoles(VardaKayttooikeusRoles.HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA)
      },
      toimijatiedot: {
        katselija: getRoles(VardaKayttooikeusRoles.TOIMIJATIEDOT_TALLENTAJA, VardaKayttooikeusRoles.TOIMIJATIEDOT_KATSELIJA),
        tallentaja: getRoles(VardaKayttooikeusRoles.TOIMIJATIEDOT_TALLENTAJA)
      }
    };

    // filter off TALLENTAJA rights from PAOS-toimipaikat without TALLENTAJA-responsibility
    if (toimipaikka && toimipaikka.paos_organisaatio_nimi) {
      // toimipaikka-based henkilöstötiedot are disabled on PAOS
      access.tyontekijatiedot = { katselija: false, tallentaja: false };
      access.tilapainenHenkilosto = { katselija: false, tallentaja: false };
      access.taydennyskoulutustiedot = { katselija: false, tallentaja: false };

      if (!toimipaikka.paos_tallentaja_organisaatio_id_list.includes(parseInt(this.vardaVakajarjestajaService.selectedVakajarjestaja.id))) {
        Object.keys(access).forEach(key => {
          if (access[key].tallentaja) {
            access[key].tallentaja = false;
          }
        });
      }
      if (!toimipaikka.paos_tallentaja_organisaatio_id_list.length) {
        Object.keys(access).forEach(key => {
          if (access[key].katselija) {
            access[key].katselija = false;
          }
        });
      }
    }

    return access;
  }

  getUserAccessIfAnyToimipaikka(toimipaikat: Array<VardaToimipaikkaMinimalDto> | Array<VardaToimipaikkaDTO>): UserAccess {
    const userAccess = this.getUserAccess();
    toimipaikat.forEach((toimipaikka: VardaToimipaikkaMinimalDto | VardaToimipaikkaDTO) => {
      const toimipaikkaAccess = this.getUserAccess(toimipaikka.organisaatio_oid);
      userAccess.paakayttaja = userAccess.paakayttaja || toimipaikkaAccess.paakayttaja;
      Object.keys(toimipaikkaAccess).filter((key: string) => key !== 'paakayttaja').forEach((key: string) => {
        userAccess[key].katselija = userAccess[key].katselija || toimipaikkaAccess[key].katselija;
        userAccess[key].tallentaja = userAccess[key].tallentaja || toimipaikkaAccess[key].tallentaja;
      });
    });
    return userAccess;
  }

  isTilapainenHenkilostoOnly() {
    const access = this.getUserAccess();

    if (!access.tilapainenHenkilosto.katselija) {
      return false;
    }
    return !Object.entries(access)
      .filter(([accessKey, accessValue]) => accessKey !== UserAccessKeys.tilapainenHenkilosto)
      .some(([accessKey, accessValue]) => !!accessValue.katselija);
  }

  getToimipaikatWithLapsiPermissions(toimipaikat: Array<VardaToimipaikkaMinimalDto>): Array<VardaToimipaikkaMinimalDto> {
    return toimipaikat.filter(toimipaikka => {
      const toimipaikkaAccess = this.getUserAccess(toimipaikka.organisaatio_oid);
      return toimipaikkaAccess.lapsitiedot.katselija || toimipaikkaAccess.huoltajatiedot.katselija;
    });
  }

  getToimipaikatWithTyontekijaPermissions(toimipaikat: Array<VardaToimipaikkaMinimalDto>): Array<VardaToimipaikkaMinimalDto> {
    return toimipaikat.filter(toimipaikka => {
      const toimipaikkaAccess = this.getUserAccess(toimipaikka.organisaatio_oid);
      return toimipaikkaAccess.tyontekijatiedot.katselija || toimipaikkaAccess.taydennyskoulutustiedot.katselija;
    });
  }
}
