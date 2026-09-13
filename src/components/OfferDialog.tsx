import { useEffect, useRef } from 'react';
import type { OfferCopy, SiteCopy } from '../content/types';
import { Icon } from './Icon';

interface Props {
  offer: OfferCopy;
  copy: SiteCopy['common'];
  isEquipment: boolean;
  trigger: HTMLButtonElement;
  onDismiss: () => void;
}

export function OfferDialog({ offer, copy, isEquipment, trigger, onDismiss }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    dialog.showModal();
    document.body.classList.add('dialog-open');
    return () => {
      dialog.close();
      document.body.classList.remove('dialog-open');
      // Restore the exact trigger even when React removes the dialog during cleanup.
      if (trigger.isConnected) trigger.focus();
    };
  }, [trigger]);

  return (
    <dialog
      ref={dialogRef}
      className="offer-dialog"
      aria-labelledby="offer-title"
      aria-describedby="offer-summary"
      onCancel={(event) => {
        event.preventDefault();
        onDismiss();
      }}
    >
      <div className="offer-dialog__toolbar">
        <span className="eyebrow">{copy.concept}</span>
        <button type="button" className="icon-button" aria-label={copy.close} onClick={onDismiss}>
          <Icon name="close" />
        </button>
      </div>
      <div className="offer-dialog__body">
        <h2 id="offer-title">{offer.title}</h2>
        <p id="offer-summary" className="offer-dialog__summary">
          {offer.summary}
        </p>
        <p>{offer.description}</p>
        <h3>{copy.included}</h3>
        <ul className="included-list">
          {offer.includes.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <p className="concept-note">{isEquipment ? copy.equipmentNote : copy.offerNote}</p>
      </div>
    </dialog>
  );
}
