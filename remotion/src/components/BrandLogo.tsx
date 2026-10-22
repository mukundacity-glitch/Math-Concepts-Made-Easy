import {Img, staticFile} from 'remotion';

/** Single canonical version-controlled logo for every Remotion slide. */
export const BRAND_LOGO_ASSET = 'branding/math-concepts-made-easy-logo.webp';

export const BrandLogo = ({size = 72}: {readonly size?: number}) => (
  <Img
    src={staticFile(BRAND_LOGO_ASSET)}
    width={size}
    height={size}
    alt="Math Concepts Made Easy"
    style={{width: size, height: size, objectFit: 'contain', flexShrink: 0}}
  />
);
