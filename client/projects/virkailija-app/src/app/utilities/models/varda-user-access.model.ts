export enum UserAccessKeys {
  lapsitiedot = 'lapsitiedot',
  huoltajatiedot = 'huoltajatiedot',
  tyontekijatiedot = 'tyontekijatiedot',
  tilapainenHenkilosto = 'tilapainenHenkilosto',
  taydennyskoulutustiedot = 'taydennyskoulutustiedot',
  toimijatiedot = 'toimijatiedot',
  raportit = 'raportit',
  oph = 'oph',
}

export enum UserAccessTypes {
  katselija = 'katselija',
  tallentaja = 'tallentaja'
}

export interface UserAccess {
  paakayttaja?: boolean;
  [UserAccessKeys.lapsitiedot]?: UserAccessPart;
  [UserAccessKeys.huoltajatiedot]?: UserAccessPart;
  [UserAccessKeys.tyontekijatiedot]?: UserAccessPart;
  [UserAccessKeys.tilapainenHenkilosto]?: UserAccessPart;
  [UserAccessKeys.taydennyskoulutustiedot]?: UserAccessPart;
  [UserAccessKeys.toimijatiedot]?: UserAccessPart;
  [UserAccessKeys.raportit]?: UserAccessPart;
  [UserAccessKeys.oph]?: UserAccessPart;
}

interface UserAccessPart {
  [UserAccessTypes.katselija]?: boolean;
  [UserAccessTypes.tallentaja]?: boolean;
}

export enum SaveAccess {
  kaikki = 'kaikki_save',
  lapsitiedot = 'lapsitiedot_save',
  henkilostotiedot = 'henkilostotiedot_save',
  tyontekijatiedot = 'tyontekijatiedot_save',
}

export enum ViewAccess {
  kaikki = 'kaikki_view',
  lapsitiedot = 'lapsitiedot_view',
  henkilostotiedot = 'henkilostotiedot_view',
  tyontekijatiedot = 'tyontekijatiedot_view'
}
