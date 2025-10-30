export const sortByAlkamisPvm = (a, b) => {
  const alkamisPvmA = a.alkamis_pvm;
  const alkamisPvmB = b.alkamis_pvm;
  return alkamisPvmA === alkamisPvmB ? 0 : alkamisPvmA < alkamisPvmB ? 1 : -1;
};

export const sortBySuoritusPvm = (a, b) => {
  const suoritusPvmA = a.suoritus_pvm;
  const suoritusPvmB = b.suoritus_pvm;
  return suoritusPvmA === suoritusPvmB ? 0 : suoritusPvmA < suoritusPvmB ? 1 : -1;
};

export const sortByName = (a, b) => {
  const nameA = a.name;
  const nameB = b.name;
  return nameA === nameB ? 0 : nameA > nameB ? 1 : -1;
};

export const sortByTutkintoKoodi = (a, b, listOfStrings: Array<string> = []) => {
  const indexA = listOfStrings.indexOf(a.tutkinto_koodi);
  const indexB = listOfStrings.indexOf(b.tutkinto_koodi);
  return indexA === indexB ? 0 : indexA > indexB ? 1 : -1;
};

export const extractCursor = (url: string | null): string | null => {
  if (!url) return null;

  try {
    const base = window.location.origin; // fallback base
    const urlObj = new URL(url, base);
    return urlObj.searchParams.get('cursor');
  } catch {
    console.warn('Could not parse cursor URL:', url);
    return null;
  }
};
