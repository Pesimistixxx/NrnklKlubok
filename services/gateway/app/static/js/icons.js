/** Shared stroke SVG icons for MKG UI (20px default). */
(function () {
  function svgIcon(paths, size = 20, className = "icon-svg") {
    const cls = className ? ` class="${className}"` : "";
    return `<svg${cls} width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`;
  }

  window.MKG_ICONS = {
    paperclip(size = 20, className = "icon-svg") {
      return svgIcon(
        '<path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>',
        size,
        className
      );
    },
    upload(size = 20, className = "icon-svg") {
      return svgIcon(
        '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
        size,
        className
      );
    },
  };
})();
