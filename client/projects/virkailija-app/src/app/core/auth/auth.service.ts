import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { VardaVakajarjestajaService } from '../services/varda-vakajarjestaja.service';
import { VardaKayttooikeusRoles, VardaToimipaikkaDTO, VardaVakajarjestajaUi } from '../../utilities/models';
import { VardaToimipaikkaMinimalDto } from '../../utilities/models/dto/varda-toimipaikka-dto.model';
import { SaveAccess, UserAccess, UserAccessKeys, ViewAccess } from '../../utilities/models/varda-user-access.model';
import { environment } from 'projects/huoltaja-app/src/environments/environment';
import { filter } from 'rxjs/operators';
import { VardaUserDTO } from 'varda-shared';
import { VardaKayttajatyyppi } from '../../../../../varda-shared/src/lib/models/varda-kayttajatyyppi.enum';

class Kayttooikeus {
  kayttooikeus: VardaKayttooikeusRoles;
  organisaatio: string;
}

@Injectable()
export class AuthService {

  selectedVakajarjestaja: VardaVakajarjestajaUi;
  allToimipaikat: Array<VardaToimipaikkaMinimalDto>;
  loggedInUserKayttooikeudet: Array<Kayttooikeus> = [];
  loggedInUserAfterAuthCheckUrl: string;
  selectedOrganisationLevelKayttooikeusRole: string;
  hasToimipaikkaLevelTallentajaRole: boolean;
  redirectUrl: string;
  isAdminUser = false;
  isOPHUser = false;
  loggedInUserVakajarjestajaLevelKayttooikeudet: Array<Kayttooikeus> = [];
  loggedInUserToimipaikkaLevelKayttooikeudet: Array<Kayttooikeus> = [];
  toimipaikkaAccessToAnyToimipaikka$ = new BehaviorSubject<UserAccess>(null);

  constructor(
    private vardaVakajarjestajaService: VardaVakajarjestajaService
  ) {
    /** when login process has fetched toimipaikat its time to assign user access */
    this.vardaVakajarjestajaService.getToimipaikat().pipe(filter(Boolean)).subscribe((toimipaikat: Array<VardaToimipaikkaMinimalDto>) => {
      this.selectedVakajarjestaja = this.vardaVakajarjestajaService.getSelectedVakajarjestaja();
      this.allToimipaikat = toimipaikat;
      this.initUserAccess(toimipaikat);

      this.vardaVakajarjestajaService.setFilteredToimipaikat({
        toimipaikat: toimipaikat,
        katselijaToimipaikat: this.getAuthorizedToimipaikat(toimipaikat),
        tallentajaToimipaikat: this.getAuthorizedToimipaikat(toimipaikat, SaveAccess.kaikki)
      });
    });
  }

  initUserAccess(toimipaikat: Array<VardaToimipaikkaDTO>): void {
    this.loggedInUserVakajarjestajaLevelKayttooikeudet = this.loggedInUserKayttooikeudet.filter(kayttooikeus =>
      kayttooikeus.organisaatio === this.selectedVakajarjestaja.organisaatio_oid
    );

    this.loggedInUserToimipaikkaLevelKayttooikeudet = this.loggedInUserKayttooikeudet.filter(
      kayttooikeus => toimipaikat.some(toimipaikka => toimipaikka.organisaatio_oid === kayttooikeus.organisaatio)
    );

    const toimipaikkaAccessIfAny = this.getUserAccessIfAnyToimipaikka(toimipaikat);
    this.toimipaikkaAccessToAnyToimipaikka$.next(toimipaikkaAccessIfAny);

    // these parts are just for simply printing your user access in the selected organization
    const userAccessToConsole = {
      [this.selectedVakajarjestaja.nimi]: this.loggedInUserVakajarjestajaLevelKayttooikeudet.map(kayttooikeus => kayttooikeus.kayttooikeus),
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

  getAuthorizedToimipaikat(toimipaikat: Array<VardaToimipaikkaMinimalDto>, hasAccess?: SaveAccess | ViewAccess): Array<VardaToimipaikkaMinimalDto> {
    return toimipaikat.filter((toimipaikka: VardaToimipaikkaMinimalDto) => {
      const access = this.getUserAccess(toimipaikka.organisaatio_oid);

      switch (hasAccess) {
        case SaveAccess.kaikki:
          return (access.tyontekijatiedot.tallentaja || access.taydennyskoulutustiedot.tallentaja || access.huoltajatiedot.tallentaja || access.lapsitiedot.tallentaja);
        case SaveAccess.lapsitiedot:
          return (access.huoltajatiedot.tallentaja || access.lapsitiedot.tallentaja);
        case SaveAccess.henkilostotiedot:
          return (access.tyontekijatiedot.tallentaja || access.taydennyskoulutustiedot.tallentaja);
        case SaveAccess.tyontekijatiedot:
          return (access.tyontekijatiedot.tallentaja);
        case ViewAccess.lapsitiedot:
          return (access.huoltajatiedot.katselija || access.lapsitiedot.katselija);
        case ViewAccess.henkilostotiedot:
          return (access.tyontekijatiedot.katselija || access.taydennyskoulutustiedot.katselija);
        case ViewAccess.tyontekijatiedot:
          return (access.tyontekijatiedot.katselija);
        case ViewAccess.kaikki:
        case undefined:
          return (access.tyontekijatiedot.katselija || access.taydennyskoulutustiedot.katselija || access.huoltajatiedot.katselija || access.lapsitiedot.katselija);
        default:
          console.error('GetAuthorizedToimipaikat called with incorrect value', hasAccess);
          return false;
      }
    });
  }

  setKayttooikeudet(user: VardaUserDTO): Observable<VardaUserDTO> {
    return new Observable(userObs => {
      if (user.kayttajatyyppi === VardaKayttajatyyppi.VIRKAILIJA) {
        // pass
      } else if (user.kayttajatyyppi === VardaKayttajatyyppi.ADMIN) {
        this.isAdminUser = true;
        this.isOPHUser = true;
      } else if (user.kayttajatyyppi === VardaKayttajatyyppi.OPH_STAFF) {
        this.isOPHUser = true;
      } else {
        return userObs.error({ isPalvelukayttaja: true });
      }

      this.loggedInUserKayttooikeudet = user.kayttooikeudet;
      userObs.next(user);
      userObs.complete();
    });

  }

  isCurrentUserSelectedVakajarjestajaRole(...roles: VardaKayttooikeusRoles[]): boolean {
    // Admin-user has TALLENTAJA-permissions on VakaJarjestaja-level
    if (this.isAdminUser && !roles.includes(VardaKayttooikeusRoles.VARDA_PAAKAYTTAJA)) {
      return true;
    }

    return this.loggedInUserVakajarjestajaLevelKayttooikeudet
      .filter(kayttooikeus => kayttooikeus.organisaatio === this.selectedVakajarjestaja?.organisaatio_oid)
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

    const toimipaikka = this.allToimipaikat?.find(_toimipaikka => _toimipaikka.organisaatio_oid === toimipaikkaOID);

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
      },
      raportit: {
        katselija: getRoles(VardaKayttooikeusRoles.RAPORTTIEN_KATSELIJA),
        tallentaja: false
      },
      oph: {
        katselija: this.isOPHUser,
        tallentaja: this.isOPHUser
      }
    };

    // filter off TALLENTAJA rights from PAOS-toimipaikat without TALLENTAJA-responsibility
    if (toimipaikka && toimipaikka.paos_organisaatio_nimi) {
      // toimipaikka-based henkilöstötiedot are disabled on PAOS
      access.tyontekijatiedot = { katselija: false, tallentaja: false };
      access.tilapainenHenkilosto = { katselija: false, tallentaja: false };
      access.taydennyskoulutustiedot = { katselija: false, tallentaja: false };

      if (!toimipaikka.paos_tallentaja_organisaatio_id_list.includes(this.selectedVakajarjestaja.id)) {
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


  /**
   * returns true if you have access only to one or more of these keys, but not to anything else
   * eg. with tilapäpäinen henkilöstö-only
   * @param accessKeys - checks from toimipaikkaAccessToAnyToimipaikka
   * @param toimijaOnly - turns the check to toimijaAccess only
  */
  hasAccessOnlyTo(accessKeys: Array<UserAccessKeys>, toimijaOnly?: boolean): boolean {
    const access = toimijaOnly ? this.getUserAccess() : this.toimipaikkaAccessToAnyToimipaikka$.getValue();

    const hasAccessTo = Object.entries(access)
      .filter(([accessKey, accessValue]) => accessValue?.katselija)
      .map(([accessKey, accessValue]) => accessKey as UserAccessKeys);

    const requiredAccess = hasAccessTo.find(accessKey => accessKeys.includes(accessKey));
    const excessAccess = hasAccessTo.find(accessKey => !accessKeys.includes(accessKey));

    // check if atleast one key is a hit and nothing else is found
    return requiredAccess && !excessAccess;
  }

}
