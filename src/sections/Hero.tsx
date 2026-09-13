import type { SiteCopy } from '../content/types';

export function Hero({ copy }: { copy: SiteCopy['hero'] }) {
  return (
    <section className="hero" aria-labelledby="hero-title">
      <div className="hero__art">
        <img
          src="/images/hero.png"
          width="1536"
          height="1024"
          alt={copy.imageAlt}
          fetchPriority="high"
          decoding="async"
        />
      </div>
      <div className="hero__copy container">
        <h1 id="hero-title">
          {copy.line1}
          <br />
          <span>{copy.line2}</span>
        </h1>
        <p>{copy.description}</p>
        <a className="button button--primary" href="#programmes">
          {copy.action}
        </a>
      </div>
    </section>
  );
}
