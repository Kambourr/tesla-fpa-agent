/**
 * Pen tick in the masthead. Decorative only.
 * Ticks on figures are a later task and must stay keyboard-focusable.
 */
export function MastheadMark() {
  return (
    <svg className="masthead-mark" viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <path
        d="M6.5 17.4c1.9 1.5 3.6 4 4.9 6.4C15.4 16.6 19.8 10.8 26.5 6"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.1"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
