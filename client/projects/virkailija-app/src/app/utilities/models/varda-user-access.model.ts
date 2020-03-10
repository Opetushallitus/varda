export interface UserAccess {
  paakayttaja: boolean,
  lapsitiedot: UserAccessPart,
  huoltajatiedot: UserAccessPart,
  henkilostotiedot: UserAccessPart,
  tilapainen_henkilosto: UserAccessPart;
  taydennyskoulutustiedot: UserAccessPart;
}

interface UserAccessPart {
  katselija: boolean,
  tallentaja: boolean
}

export enum SaveAccess {
  kaikki = "kaikki",
  lapsitiedot = "lapsitiedot",
  henkilostotiedot = "henkilostotiedot"
}
