import { VirkailijaTranslations } from '../../../../assets/i18n/virkailija-translations.enum';


export enum ReportStatus {
  PENDING = 'PENDING',
  CREATING = 'CREATING',
  FINISHED = 'FINISHED',
  FAILED = 'FAILED'
}

export const ReportStatusTranslations = {
  [ReportStatus.PENDING]: VirkailijaTranslations.status_pending,
  [ReportStatus.CREATING]: VirkailijaTranslations.status_creating,
  [ReportStatus.FINISHED]: VirkailijaTranslations.status_finished,
  [ReportStatus.FAILED]: VirkailijaTranslations.status_failed,
};
