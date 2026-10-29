import {createContext} from 'react';

/** Only the portable player supplies this context; production keeps staticFile URLs. */
export const PreviewAssets = createContext<Readonly<Record<string, string>> | null>(null);
