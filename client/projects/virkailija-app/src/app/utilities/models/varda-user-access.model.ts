export enum UserAccessKeys {
  lapsitiedot = 'lapsitiedot',
  huoltajatiedot = 'huoltajatiedot',
  tyontekijatiedot = 'tyontekijatiedot',
  tilapainenHenkilosto = 'tilapainenHenkilosto',
  taydennyskoulutustiedot = 'taydennyskoulutustiedot',
  toimijatiedot = 'toimijatiedot'
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
  [UserAccessKeys.toimijatiedot]: UserAccessPart;
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
