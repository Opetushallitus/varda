export enum UserAccessKeys {
  lapsitiedot = 'lapsitiedot',
  huoltajatiedot = 'huoltajatiedot',
  tyontekijatiedot = 'tyontekijatiedot',
  tilapainenHenkilosto = 'tilapainenHenkilosto',
  taydennyskoulutustiedot = 'taydennyskoulutustiedot'
}

export enum UserAccessTypes {
  katselija = 'katselija',
  tallentaja = 'tallentaja'
}

export interface UserAccess {
  paakayttaja: boolean;
  [UserAccessKeys.lapsitiedot]: UserAccessPart;
  [UserAccessKeys.huoltajatiedot]: UserAccessPart;
  [UserAccessKeys.tyontekijatiedot]: UserAccessPart;
  [UserAccessKeys.tilapainenHenkilosto]: UserAccessPart;
  [UserAccessKeys.taydennyskoulutustiedot]: UserAccessPart;
}

interface UserAccessPart {
  [UserAccessTypes.katselija]: boolean;
  [UserAccessTypes.tallentaja]: boolean;
}

export enum SaveAccess {
  kaikki = 'kaikki',
  lapsitiedot = 'lapsitiedot',
  henkilostotiedot = 'henkilostotiedot',
  tyontekijatiedot = 'tyontekijatiedot',
}
