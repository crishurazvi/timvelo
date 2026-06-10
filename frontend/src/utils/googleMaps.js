export function makeWalkingUrl(origin, destination) {
  if (!origin) return makeSearchUrl(destination);
  return `https://www.google.com/maps/dir/?api=1&origin=${origin.lat},${origin.lon}&destination=${destination.lat},${destination.lon}&travelmode=walking`;
}

export function makeSearchUrl(destination) {
  return `https://www.google.com/maps/search/?api=1&query=${destination.lat},${destination.lon}`;
}
