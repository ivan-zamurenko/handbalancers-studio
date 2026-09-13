type IconName = 'arrow' | 'close' | 'menu' | 'plus';

export function Icon({ name }: { name: IconName }) {
  const paths: Record<IconName, string> = {
    arrow: 'M5 12h14m-6-6 6 6-6 6',
    close: 'm6 6 12 12M6 18 18 6',
    menu: 'M4 8h16M4 16h16',
    plus: 'M5 12h14M12 5v14',
  };
  return (
    <svg className="icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d={paths[name]}
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
