export type Locale = 'uk' | 'en';

export type OfferKind = 'programme' | 'package' | 'consultation' | 'equipment';
export type OfferId =
  | 'handstand'
  | 'mobility'
  | 'flexibility'
  | 'programme'
  | 'studio'
  | 'coach'
  | 'consultation'
  | 'bundle'
  | 'parallettes'
  | 'mat'
  | 'blocks';

export interface OfferCopy {
  title: string;
  summary: string;
  description: string;
  includes: readonly string[];
}

export interface SiteCopy {
  navigation: {
    label: string;
    home: string;
    programmes: string;
    method: string;
    coaching: string;
    equipment: string;
    openMenu: string;
    closeMenu: string;
    language: string;
    skip: string;
  };
  hero: { line1: string; line2: string; description: string; action: string; imageAlt: string };
  programmes: { eyebrow: string; title: string; description: string; imageAlt: string };
  method: {
    eyebrow: string;
    title: string;
    description: string;
    steps: readonly { title: string; body: string }[];
  };
  coaching: {
    eyebrow: string;
    title: string;
    description: string;
    compareLabel: string;
    bundleLabel: string;
  };
  equipment: { eyebrow: string; title: string; description: string; imageAlt: string };
  future: { eyebrow: string; title: string; body: string; items: readonly string[] };
  faq: {
    eyebrow: string;
    title: string;
    items: readonly {
      id: 'start' | 'mobility' | 'coaching' | 'platform';
      question: string;
      answer: string;
    }[];
  };
  footer: { title: string; action: string; note: string; top: string };
  common: {
    details: string;
    close: string;
    concept: string;
    included: string;
    offerNote: string;
    equipmentNote: string;
    photoNote: string;
  };
  offers: Record<OfferId, OfferCopy>;
}
