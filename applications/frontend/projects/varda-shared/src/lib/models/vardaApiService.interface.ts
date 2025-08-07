export interface VardaApiServiceInterface {
  getTranslationCategory(): string;
  getLocalizationApi(): string;
  getTranslationEnum(): Record<string, string>;
}
