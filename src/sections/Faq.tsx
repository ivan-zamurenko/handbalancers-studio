import type { SiteCopy } from '../content/types';
import { Icon } from '../components/Icon';

export function Faq({ copy }: { copy: SiteCopy['faq'] }) {
  return (
    <section id="faq" className="section faq container" aria-labelledby="faq-title">
      <div className="section-heading">
        <p className="eyebrow">{copy.eyebrow}</p>
        <h2 id="faq-title">{copy.title}</h2>
      </div>
      <div className="faq__items">
        {copy.items.map((item) => (
          <details key={item.id}>
            <summary>
              {item.question}
              <Icon name="plus" />
            </summary>
            <p>{item.answer}</p>
          </details>
        ))}
      </div>
    </section>
  );
}
