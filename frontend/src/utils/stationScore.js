export function markerClass(color) {
  if (color === "green") return "marker-green";
  if (color === "orange") return "marker-orange";
  if (color === "red") return "marker-red";
  return "marker-gray";
}

export function stationProblemLabel(station) {
  if (!station) return "";
  if (station.status === "Offline") return "Offline";
  if (station.bikes_available === 0 && station.empty_doors === 0) return "Date suspecte";
  if (station.bikes_available === 0) return "Fără biciclete";
  if (station.empty_doors === 0) return "Fără loc de retur";
  if (["Subpopulated", "Suprapopulated"].includes(station.status)) return "Status instabil";
  return "OK";
}
