import type { SiteCopy } from '../content/types';

export function Footer({ copy }: { copy: SiteCopy }) {
  return (
    <footer className="footer container">
      <div className="footer__invitation">
        <h2>{copy.footer.title}</h2>
        <a href="#programmes" className="button button--primary">
          {copy.footer.action}
        </a>
      </div>
      <div className="footer__bottom">
        <a href="#main" className="brand" aria-label={'Handbalancer’s Studio — ' + copy.footer.top}>
          Handbalancer’s Studio
        </a>
        <p>{copy.footer.note}</p>
      </div>
      <p className="photo-note">{copy.common.photoNote}</p>
    </footer>
  );
}
