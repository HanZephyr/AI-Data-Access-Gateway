if (typeof window !== "undefined" && window.getComputedStyle) {
  const getComputedStyle = window.getComputedStyle.bind(window);

  window.getComputedStyle = ((element: Element) => getComputedStyle(element)) as typeof window.getComputedStyle;
}
