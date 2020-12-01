import enum


class Koodistot(enum.Enum):
    kunta_koodit = 'kunta_koodit'
    kieli_koodit = 'kieli_koodit'
    jarjestamismuoto_koodit = 'jarjestamismuoto_koodit'
    toimintamuoto_koodit = 'toimintamuoto_koodit'
    kasvatusopillinen_jarjestelma_koodit = 'kasvatusopillinen_jarjestelma_koodit'
    toiminnallinen_painotus_koodit = 'toiminnallinen_painotus_koodit'
    tyosuhde_koodit = 'tyosuhde_koodit'
    tyoaika_koodit = 'tyoaika_koodit'
    tehtavanimike_koodit = 'tehtavanimike_koodit'
    sukupuoli_koodit = 'sukupuoli_koodit'
    tutkinto_koodit = 'tutkinto_koodit'
    maksun_peruste_koodit = 'maksun_peruste_koodit'
    lahdejarjestelma_koodit = 'lahdejarjestelma_koodit'
    postinumero_koodit = 'postinumero_koodit'
    virhe_koodit = 'virhe_koodit'

    @classmethod
    def list(cls):
        return [koodisto.value for koodisto in cls]
