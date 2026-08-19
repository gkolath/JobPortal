/** Strip HTML tags from scraped job text for safe plain-text display. */
export function stripHtml(value: string, maxLen = 0): string {
  if (!value) return "";
  let text = value;
  // Decode common entities if content was escaped
  const textarea = document.createElement("textarea");
  for (let i = 0; i < 3; i++) {
    textarea.innerHTML = text;
    const next = textarea.value;
    if (next === text) break;
    text = next;
  }
  try {
    const doc = new DOMParser().parseFromString(text, "text/html");
    text = doc.body.textContent || "";
  } catch {
    text = text.replace(/<[^>]*>/g, " ");
  }
  text = text.replace(/\u00a0/g, " ").replace(/\s+/g, " ").trim();
  if (maxLen && text.length > maxLen) {
    return `${text.slice(0, maxLen - 1).trimEnd()}…`;
  }
  return text;
}
