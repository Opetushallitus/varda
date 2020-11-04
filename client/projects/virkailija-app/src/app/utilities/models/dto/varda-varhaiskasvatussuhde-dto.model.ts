import { Lahdejarjestelma } from '../enums/hallinnointijarjestelma';

export class VardaVarhaiskasvatussuhdeDTO {
    id?: number;
    url?: string;
    varhaiskasvatuspaatos?: string;
    toimipaikka?: string;
    toimipaikka_oid?: string;
    alkamis_pvm?: string;
    paattymis_pvm?: string;
    lahdejarjestelma?: Lahdejarjestelma;
}
