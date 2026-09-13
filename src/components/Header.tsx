import { useEffect, useRef, useState } from 'react';
import type { Locale, SiteCopy } from '../content/types';
import { Icon } from './Icon';

interface Props {
  locale: Locale;
  copy: SiteCopy['navigation'];
  onLocaleChange: (locale: Locale) => void;
}

export function Header({ locale, copy, onLocaleChange }: Props) {
  const [open, setOpen] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);
  const navigation = useRef<HTMLElement>(null);

  useEffect(() => {
    const desktop = window.matchMedia('(min-width: 900px)');
    const onResize = () => {
      if (desktop.matches) setOpen(false);
    };
    desktop.addEventListener('change', onResize);
    return () => desktop.removeEventListener('change', onResize);
  }, []);

  useEffect(() => {
    if (!open) return;
    // The trigger follows navigation in the DOM; opening must lead into the links.
    navigation.current?.querySelector<HTMLAnchorElement>('a')?.focus();
    const onEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false);
        menuButton.current?.focus();
      }
    };
    document.addEventListener('keydown', onEscape);
    return () => document.removeEventListener('keydown', onEscape);
  }, [open]);

  return (
    <header className="header" id="top">
      <div className="header__inner container">
        <a
          className="brand"
          href="#main"
          aria-label={'Handbalancer’s Studio — ' + copy.home}
          onClick={() => setOpen(false)}
        >
          Handbalancer’s <span>Studio</span>
        </a>
        <nav
          ref={navigation}
          id="site-navigation"
          className={'navigation' + (open ? ' navigation--open' : '')}
          aria-label={copy.label}
        >
          {(['programmes', 'method', 'coaching', 'equipment'] as const).map((id) => (
            <a key={id} href={'#' + id} onClick={() => setOpen(false)}>
              {copy[id]}
            </a>
          ))}
        </nav>
        <div className="header__actions">
          <fieldset className="language">
            <legend className="sr-only">{copy.language}</legend>
            <button
              type="button"
              lang="uk"
              aria-label="Українська"
              aria-pressed={locale === 'uk'}
              onClick={() => onLocaleChange('uk')}
            >
              УКР
            </button>
            <span aria-hidden="true">/</span>
            <button
              type="button"
              lang="en"
              aria-label="English"
              aria-pressed={locale === 'en'}
              onClick={() => onLocaleChange('en')}
            >
              EN
            </button>
          </fieldset>
          <button
            ref={menuButton}
            type="button"
            className="menu-button icon-button"
            aria-label={open ? copy.closeMenu : copy.openMenu}
            aria-expanded={open}
            aria-controls="site-navigation"
            onClick={() => setOpen(!open)}
          >
            <Icon name={open ? 'close' : 'menu'} />
          </button>
        </div>
      </div>
    </header>
  );
}
