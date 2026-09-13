import { useEffect, useState } from 'react';
import { copy } from './content/copy';
import { getOfferKind } from './content/catalog';
import type { Locale, OfferId } from './content/types';
import { Header } from './components/Header';
import { Footer } from './components/Footer';
import { OfferDialog } from './components/OfferDialog';
import { Hero } from './sections/Hero';
import { Programmes } from './sections/Programmes';
import { Method } from './sections/Method';
import { Coaching } from './sections/Coaching';
import { Equipment } from './sections/Equipment';
import { Future } from './sections/Future';
import { Faq } from './sections/Faq';

interface Selection {
  id: OfferId;
  trigger: HTMLButtonElement;
}

export function App() {
  // The stakeholder selected Ukrainian; browser or location settings never override it.
  const [locale, setLocale] = useState<Locale>('uk');
  const [selection, setSelection] = useState<Selection | null>(null);
  const text = copy[locale];

  useEffect(() => {
    document.documentElement.lang = locale;
    const description = document.querySelector<HTMLMetaElement>('meta[name="description"]');
    if (description) description.content = text.hero.description;
  }, [locale, text.hero.description]);

  const openOffer = (id: OfferId, trigger: HTMLButtonElement) => setSelection({ id, trigger });

  return (
    <>
      <a className="skip-link" href="#main">
        {text.navigation.skip}
      </a>
      <Header locale={locale} copy={text.navigation} onLocaleChange={setLocale} />
      <main id="main" tabIndex={-1}>
        <Hero copy={text.hero} />
        <Programmes copy={text} onSelect={openOffer} />
        <Method copy={text.method} />
        <Coaching copy={text} onSelect={openOffer} />
        <Equipment copy={text} onSelect={openOffer} />
        <Future copy={text.future} />
        <Faq copy={text.faq} />
      </main>
      <Footer copy={text} />
      {selection && (
        <OfferDialog
          key={selection.id}
          offer={text.offers[selection.id]}
          copy={text.common}
          isEquipment={getOfferKind(selection.id) === 'equipment'}
          trigger={selection.trigger}
          onDismiss={() => setSelection(null)}
        />
      )}
    </>
  );
}
