import { catalogue } from '../content/catalog';
import type { SiteCopy } from '../content/types';
import { OfferButton, type OpenOffer } from '../components/OfferButton';

export function Programmes({ copy, onSelect }: { copy: SiteCopy; onSelect: OpenOffer }) {
  return (
    <section
      id="programmes"
      className="section programmes container"
      aria-labelledby="programmes-title"
    >
      <div className="section-heading">
        <p className="eyebrow">{copy.programmes.eyebrow}</p>
        <h2 id="programmes-title">{copy.programmes.title}</h2>
        <p>{copy.programmes.description}</p>
      </div>
      <div className="programmes__layout">
        <div className="offer-list">
          {catalogue
            .filter((offer) => offer.kind === 'programme')
            .map(({ id }, index) => (
              <article className="programme-row" key={id}>
                <span className="row-number" aria-hidden="true">
                  {'0' + (index + 1)}
                </span>
                <div>
                  <h3>{copy.offers[id].title}</h3>
                  <p>{copy.offers[id].summary}</p>
                  <OfferButton
                    id={id}
                    offer={copy.offers[id]}
                    label={copy.common.details}
                    onSelect={onSelect}
                  />
                </div>
              </article>
            ))}
        </div>
        <figure className="practice-photo">
          <img
            src="/images/practice.png"
            width="1536"
            height="1024"
            alt={copy.programmes.imageAlt}
            loading="lazy"
            decoding="async"
          />
        </figure>
      </div>
    </section>
  );
}
