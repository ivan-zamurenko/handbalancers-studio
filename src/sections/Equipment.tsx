import { catalogue } from '../content/catalog';
import type { SiteCopy } from '../content/types';
import { OfferButton, type OpenOffer } from '../components/OfferButton';

export function Equipment({ copy, onSelect }: { copy: SiteCopy; onSelect: OpenOffer }) {
  return (
    <section
      id="equipment"
      className="section equipment container"
      aria-labelledby="equipment-title"
    >
      <div className="section-heading">
        <p className="eyebrow">{copy.equipment.eyebrow}</p>
        <h2 id="equipment-title">{copy.equipment.title}</h2>
        <p>{copy.equipment.description}</p>
      </div>
      <div className="equipment__layout">
        <figure className="equipment-photo">
          <img
            src="/images/equipment.png"
            width="1536"
            height="1024"
            alt={copy.equipment.imageAlt}
            loading="lazy"
            decoding="async"
          />
        </figure>
        <div className="equipment__list">
          {catalogue
            .filter((offer) => offer.kind === 'equipment')
            .map(({ id }) => (
              <article className="equipment-row" key={id}>
                <h3>{copy.offers[id].title}</h3>
                <p>{copy.offers[id].summary}</p>
                <OfferButton
                  id={id}
                  offer={copy.offers[id]}
                  label={copy.common.details}
                  onSelect={onSelect}
                />
              </article>
            ))}
        </div>
      </div>
      <p className="section-note">{copy.common.equipmentNote}</p>
    </section>
  );
}
