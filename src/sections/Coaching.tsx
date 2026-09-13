import { catalogue } from '../content/catalog';
import type { SiteCopy } from '../content/types';
import { OfferButton, type OpenOffer } from '../components/OfferButton';

export function Coaching({ copy, onSelect }: { copy: SiteCopy; onSelect: OpenOffer }) {
  return (
    <section id="coaching" className="section coaching container" aria-labelledby="coaching-title">
      <div className="coaching__intro">
        <div className="section-heading">
          <p className="eyebrow">{copy.coaching.eyebrow}</p>
          <h2 id="coaching-title">{copy.coaching.title}</h2>
          <p>{copy.coaching.description}</p>
        </div>
        <article className="consultation">
          <h3>{copy.offers.consultation.title}</h3>
          <p>{copy.offers.consultation.description}</p>
          <OfferButton
            id="consultation"
            offer={copy.offers.consultation}
            label={copy.common.details}
            onSelect={onSelect}
          />
        </article>
      </div>
      <section className="packages" aria-label={copy.coaching.compareLabel}>
        {catalogue
          .filter((offer) => offer.kind === 'package')
          .map(({ id }) => (
            <article className="package" key={id}>
              <h3>{copy.offers[id].title}</h3>
              <p className="package__summary">{copy.offers[id].summary}</p>
              <ul className="included-list">
                {copy.offers[id].includes.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              <OfferButton
                id={id}
                offer={copy.offers[id]}
                label={copy.common.details}
                onSelect={onSelect}
                className="button button--secondary"
              />
            </article>
          ))}
      </section>
      <article className="bundle">
        <div>
          <p className="eyebrow">{copy.coaching.bundleLabel}</p>
          <h3>{copy.offers.bundle.title}</h3>
          <p>{copy.offers.bundle.summary}</p>
        </div>
        <OfferButton
          id="bundle"
          offer={copy.offers.bundle}
          label={copy.common.details}
          onSelect={onSelect}
        />
      </article>
      <p className="section-note">{copy.common.offerNote}</p>
    </section>
  );
}
