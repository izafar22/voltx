// Original editorial diagrams. Text in the repair journey provides the meaning;
// these coordinated SVG accents are decorative, not electrical instructions.
export function ProcessIllustration({ step }) {
  const ink = "hsl(var(--brand-foreground))";
  const surface = "hsl(var(--card))";
  const soft = "hsl(var(--brand-surface))";
  const line = "hsl(var(--brand-border))";
  const diagrams = [
    <g key="enquiry">
      <path d="M48 20 108 27 108 85 48 78Z" fill={surface} />
      <path d="m108 27 6-4v57l-6 5M48 20l6-4 60 7" fill={soft} />
      <path d="M58 32 96 37v23L58 55Z" fill={soft} />
      <path d="m69 39 15 2v12l-15-2Z" />
      <path d="m61 65 33 4m-33 4 23 3" />
    </g>,
    <g key="assessment">
      <path d="m39 49 49-21 35 19-49 22Z" fill={soft} />
      <path d="m39 49 35 20 49-22v10L74 79 39 59Z" fill={surface} />
      <path d="m58 48 20-9 16 9-20 9Z" fill={surface} />
      <circle cx="95" cy="36" r="17" fill={surface} />
      <circle cx="95" cy="36" r="11" fill={soft} />
      <path d="m107 49 16 20" strokeWidth="6" />
    </g>,
    <g key="quotation">
      <path d="m51 22 57 6v58l-57-6Z" fill={surface} />
      <path d="m108 28 6-4v56l-6 6M51 22l6-4 57 6" fill={soft} />
      <path d="m68 20 21 2v9l-21-2Z" fill={soft} />
      <path d="m62 43 32 4m-32 7 32 4m-32 7 19 2" />
      <path d="m88 71 19-7 15 9-19 8Z" fill={soft} />
    </g>,
    <g key="testing">
      <path d="m27 70 36-16 30 17-36 16Z" fill={soft} />
      <path d="m45 69 16-7 13 7-16 7Z" fill={surface} />
      <path d="m86 25 39 5v36l-39-5Z" fill={surface} />
      <path d="m92 34 26 3v19l-26-3Z" fill={soft} />
      <path d="m95 46 5-3 4 6 5-8 6 5m-11 18v11m-10 4 22 2M79 73l11-8" />
    </g>,
    <g key="return">
      <path d="m41 42 37-18 41 23-38 18Z" fill={soft} />
      <path d="m41 42 40 23v28L41 70Z" fill={surface} />
      <path d="m81 65 38-18v28L81 93Z" fill={soft} />
      <path d="m59 33 40 23v11m-46-9 15 9m-15-1 10 6" />
      <path d="m107 73 19 3v21l-19-3Z" fill={surface} />
      <path d="m112 82 8 1m-8 5 6 1" />
    </g>,
  ];
  if (!diagrams[step]) return null;
  return (
    <svg
      viewBox="0 0 160 112"
      width="160"
      height="112"
      className="rx-process-art"
      aria-hidden="true"
      focusable="false"
    >
      <path d="m22 85 57-27 60 31-57 24Z" fill={soft} />
      <g
        stroke={ink}
        strokeWidth="1.8"
        strokeLinejoin="round"
        strokeLinecap="round"
        fill="none"
      >
        {diagrams[step]}
      </g>
      <path d="m27 97 19 9m77-2 12-6" stroke={line} strokeWidth="1.2" />
    </svg>
  );
}
