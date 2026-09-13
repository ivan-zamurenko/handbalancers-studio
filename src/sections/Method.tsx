import type { SiteCopy } from '../content/types';

export function Method({ copy }: { copy: SiteCopy['method'] }) {
  return (
    <section id="method" className="section method" aria-labelledby="method-title">
      <div className="container">
        <div className="section-heading section-heading--center">
          <p className="eyebrow">{copy.eyebrow}</p>
          <h2 id="method-title">{copy.title}</h2>
          <p>{copy.description}</p>
        </div>
        <ol className="method__steps">
          {copy.steps.map((step, index) => (
            <li key={step.title}>
              <span className="step-number" aria-hidden="true">
                {'0' + (index + 1)}
              </span>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
