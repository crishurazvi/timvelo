export function formatDateTime(value) {
  if (!value) return "N/A";
  try {
    return new Intl.DateTimeFormat("ro-RO", {
      dateStyle: "short",
      timeStyle: "short"
    }).format(new Date(value));
  } catch (_) {
    return value;
  }
}

export function clampText(value, max = 80) {
  if (!value) return "";
  return value.length > max ? `${value.slice(0, max)}...` : value;
}
