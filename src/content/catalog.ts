import type { OfferId, OfferKind } from './types';

// Stable IDs let copy, rendering and future data sources evolve independently.
export const catalogue = [
  { id: 'handstand', kind: 'programme' },
  { id: 'mobility', kind: 'programme' },
  { id: 'flexibility', kind: 'programme' },
  { id: 'programme', kind: 'package' },
  { id: 'studio', kind: 'package' },
  { id: 'coach', kind: 'package' },
  { id: 'consultation', kind: 'consultation' },
  { id: 'bundle', kind: 'consultation' },
  { id: 'parallettes', kind: 'equipment' },
  { id: 'mat', kind: 'equipment' },
  { id: 'blocks', kind: 'equipment' },
] as const satisfies readonly { id: OfferId; kind: OfferKind }[];

export function getOfferKind(id: OfferId): OfferKind {
  const offer = catalogue.find((entry) => entry.id === id);
  if (!offer) throw new Error(`Unknown offer ID: ${id}`);
  return offer.kind;
}
