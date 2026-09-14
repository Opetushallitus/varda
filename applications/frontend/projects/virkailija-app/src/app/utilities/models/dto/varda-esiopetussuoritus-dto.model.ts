export class VardaEsiopetussuoritusDTO {
    url?: string;
    esiopetuspaatos?: string;
    e_perusteviittaus?: string;
    suorituskieli_koodi?: string;
    muut_suorituskielet_koodi?: Array<string>;
    tutkinto_koodi?: string;
    tutkinnon_myontaja?: string;
    kielikylpykielet_koodi?: Array<string>;
}
