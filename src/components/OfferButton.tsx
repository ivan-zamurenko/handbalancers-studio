import type { OfferCopy, OfferId } from '../content/types';
import { Icon } from './Icon';

export type OpenOffer = (id: OfferId, trigger: HTMLButtonElement) => void;

interface Props {
  id: OfferId;
  offer: OfferCopy;
  label: string;
  onSelect: OpenOffer;
  className?: string;
}

export function OfferButton({ id, offer, label, onSelect, className = 'text-action' }: Props) {
  return (
    <button
      type="button"
      className={className}
      aria-label={label + ': ' + offer.title}
      aria-haspopup="dialog"
      onClick={(event) => onSelect(id, event.currentTarget)}
    >
      {label}
      <Icon name="arrow" />
    </button>
  );
}
