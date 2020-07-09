export class VardaVarhaiskasvatuspaatosDTO {
    id?: number;
    url?: string;
    lapsi?: string;
    vuorohoito_kytkin?: boolean;
    pikakasittely_kytkin?: boolean;
    tuntimaara_viikossa?: any;
    paivittainen_vaka_kytkin?: boolean;
    kokopaivainen_vaka_kytkin?: boolean;
    jarjestamismuoto_koodi?: string;
    hakemus_pvm?: string;
    alkamis_pvm?: string;
    paattymis_pvm?: string;
}
