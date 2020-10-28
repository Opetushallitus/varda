import { Injectable } from '@angular/core';
import {
  VardaLapsiDTO, VardaToimipaikkaDTO, VardaVakajarjestaja, VardaVakajarjestajaUi,
  VardaVarhaiskasvatussuhdeDTO
} from '../../utilities/models';
import { BehaviorSubject, Observable, Subject } from 'rxjs';
import { AuthService } from '../auth/auth.service';
import { VardaToimipaikkaMinimalDto } from '../../utilities/models/dto/varda-toimipaikka-dto.model';
import { deprecate } from 'util';
import { LapsiByToimipaikkaDTO } from '../../utilities/models/dto/varda-henkilohaku-dto.model';
import { SaveAccess } from '../../utilities/models/varda-user-access.model';
import { VakajarjestajaToimipaikat } from '../../utilities/models/varda-vakajarjestaja-toimipaikat.model';

@Injectable()
export class VardaVakajarjestajaService {

  vakaJarjestajat: Array<VardaVakajarjestajaUi>;
  vakaJarjestajatSubject = new Subject<Array<VardaVakajarjestajaUi>>();
  selectedVakajarjestaja: VardaVakajarjestajaUi;
  selectedVakajarjestajaSubject = new BehaviorSubject<any>({});
  selectedToimipaikka: VardaToimipaikkaMinimalDto;
  selectedToimipaikkaSubject = new Subject<VardaToimipaikkaMinimalDto>();
  tallentajaToimipaikat: Array<VardaToimipaikkaMinimalDto>;
  toimipaikat: Array<VardaToimipaikkaMinimalDto>;
  tallentajaToimipaikatSubject = new Subject<Array<VardaToimipaikkaMinimalDto>>();
  toimipaikkaVarhaiskasvatussuhteet: Array<VardaVarhaiskasvatussuhdeDTO>;
  private selectedVakajarjestajaToimipaikat: VakajarjestajaToimipaikat;
  private selectedVakajarjestajaToimipaikat$ = new BehaviorSubject<VakajarjestajaToimipaikat>(null);
  constructor() { }

  getVakajarjestajat(): Array<VardaVakajarjestajaUi> {
    return this.vakaJarjestajat;
  }

  setVakajarjestajat(vardaVakaJarjestajat: Array<VardaVakajarjestajaUi>): void {
    this.vakaJarjestajat = vardaVakaJarjestajat;
    this.setVakajarjestajatSubject(vardaVakaJarjestajat);
  }

  setVakajarjestajatSubject(vardaVakaJarjestajat: Array<VardaVakajarjestajaUi>) {
    this.vakaJarjestajatSubject.next(vardaVakaJarjestajat);
  }

  getVakajarjestajatObs(): Observable<Array<VardaVakajarjestajaUi>> {
    return this.vakaJarjestajatSubject.asObservable();
  }

  setSelectedVakajarjestaja(vakajarjestaja: VardaVakajarjestajaUi, onVakajarjestajaChange?: boolean): void {
    this.selectedVakajarjestaja = vakajarjestaja;
    localStorage.setItem('varda.selectedvakajarjestaja', JSON.stringify(vakajarjestaja));
    this.setSelectedVakajarjestajaSubject(vakajarjestaja, onVakajarjestajaChange);
  }

  getSelectedVakajarjestaja(): VardaVakajarjestajaUi {
    return this.selectedVakajarjestaja;
  }

  getSelectedVakajarjestajaId(): string {
    return this.getSelectedVakajarjestaja().id;
  }

  getSelectedToimipaikka(): VardaToimipaikkaMinimalDto {
    return this.selectedToimipaikka;
  }

  setSelectedToimipaikka(toimipaikka: VardaToimipaikkaMinimalDto) {
    this.selectedToimipaikka = toimipaikka;
  }

  setSelectedToimipaikkaSubject(toimipaikka: VardaToimipaikkaMinimalDto) {
    this.selectedToimipaikkaSubject.next(toimipaikka);
  }

  getSelectedToimipaikkaObs(): Observable<VardaToimipaikkaMinimalDto> {
    return this.selectedToimipaikkaSubject.asObservable();
  }

  setSelectedVakajarjestajaSubject(vakajarjestaja: VardaVakajarjestajaUi, onVakajarjestajaChange?: boolean) {
    this.selectedVakajarjestajaSubject.next({ vakajarjestaja: vakajarjestaja, onVakajarjestajaChange: onVakajarjestajaChange });
  }

  getSelectedVakajarjestajaObs(): Observable<any> {
    return this.selectedVakajarjestajaSubject.asObservable();
  }

  getToimipaikat(): Array<VardaToimipaikkaMinimalDto> {
    return this.toimipaikat;
  }

  setToimipaikat(toimipaikat: Array<VardaToimipaikkaMinimalDto>, authService?: AuthService): void {
    this.toimipaikat = toimipaikat;
    if (authService) {
      this.setTallentajaToimipaikat(toimipaikat, authService);
      this.setVakajarjestajaToimipaikat(toimipaikat, authService);
    }
  }

  setVakajarjestajaToimipaikat(toimipaikat: Array<VardaToimipaikkaMinimalDto>, authService: AuthService): void {
    // preset allToimipaikat, as getAuthorizedToimipaikat requires it
    this.selectedVakajarjestajaToimipaikat = {
      ...this.selectedVakajarjestajaToimipaikat,
      allToimipaikat: toimipaikat
    };

    this.selectedVakajarjestajaToimipaikat = {
      allToimipaikat: toimipaikat,
      toimipaikat: toimipaikat,
      katselijaToimipaikat: authService.getAuthorizedToimipaikat(toimipaikat),
      tallentajaToimipaikat: authService.getAuthorizedToimipaikat(toimipaikat, SaveAccess.kaikki)
    };

    this.selectedVakajarjestajaToimipaikat$.next(this.selectedVakajarjestajaToimipaikat);
  }

  getVakajarjestajaToimipaikat(): VakajarjestajaToimipaikat {
    return this.selectedVakajarjestajaToimipaikat;
  }

  getVakajarjestajaToimipaikatObs(): Observable<VakajarjestajaToimipaikat> {
    return this.selectedVakajarjestajaToimipaikat$.asObservable();
  }

  getToimipaikkaAsMinimal(toimipaikka_oid: string): VardaToimipaikkaMinimalDto {
    if (this.selectedVakajarjestajaToimipaikat) {
      return this.selectedVakajarjestajaToimipaikat.allToimipaikat.find(toimipaikka => toimipaikka.organisaatio_oid === toimipaikka_oid);
    }
    return null;
  }

  /**
   * @deprecated Not working properly. Essentially returns all toimipaikat.
   */
  getTallentajaToimipaikat(): Array<VardaToimipaikkaMinimalDto> {
    return this.tallentajaToimipaikat;
  }

  /**
   * @deprecated Underlying function not working properly. Values are not what's expected.
   */
  setTallentajaToimipaikat(toimipaikat: Array<VardaToimipaikkaMinimalDto>, authService: AuthService): void {
    this.tallentajaToimipaikat = authService.getAuthorizedToimipaikat(toimipaikat);
    this.setTallentajaToimipaikatSubject(toimipaikat);
  }

  setTallentajaToimipaikatSubject(toimipaikat: Array<VardaToimipaikkaMinimalDto>) {
    this.tallentajaToimipaikatSubject.next(toimipaikat);
  }

  getTallentajaToimipaikatObs(): Observable<Array<VardaToimipaikkaMinimalDto>> {
    return this.tallentajaToimipaikatSubject.asObservable();
  }

  getVarhaiskasvatussuhteet(): Array<VardaVarhaiskasvatussuhdeDTO> {
    return this.toimipaikkaVarhaiskasvatussuhteet;
  }

  setVarhaiskasvatussuhteet(varhaiskasvatussuhteet: Array<VardaVarhaiskasvatussuhdeDTO>): void {
    this.toimipaikkaVarhaiskasvatussuhteet = varhaiskasvatussuhteet;
  }

  getVakajarjestajaByUrl(url: string, vakajarjestajat: Array<VardaVakajarjestaja>): VardaVakajarjestaja {
    return vakajarjestajat.find((t) => t.url === url);
  }
}
