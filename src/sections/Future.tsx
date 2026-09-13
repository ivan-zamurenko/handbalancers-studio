import type { SiteCopy } from '../content/types';

export function Future({ copy }: { copy: SiteCopy['future'] }) {
  return (
    <section id="future" className="section future" aria-labelledby="future-title">
      <div className="container future__layout">
        <div className="section-heading">
          <p className="eyebrow">{copy.eyebrow}</p>
          <h2 id="future-title">{copy.title}</h2>
        </div>
        <div>
          <p className="future__body">{copy.body}</p>
          <ul className="future__list">
            {copy.items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
