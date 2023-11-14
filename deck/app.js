import { MapboxOverlay as DeckOverlay } from "@deck.gl/mapbox";
import maplibregl from "maplibre-gl";

import { DebugH3TileLayer, createH3TileLayer } from "./h3-tile-layer";

let table;
let column;

function populateColumnSelect(t) {
  fetch(`http://localhost:8000/${t}`)
    .then((response) => response.json())
    .then((columns) => {
      const columnSelect = document.getElementById("columnSelect");
      columns.forEach((column) => {
        const option = document.createElement("option");
        option.value = column;
        option.text = column;
        columnSelect.appendChild(option);
      });
      column = [columns[0]];
      deck.setProps({
        layers: [...layers.slice(0, -1), createH3TileLayer(table, column)],
      });
    })
    .catch((error) => console.error("Error:", error));
}

function populateTableSelect() {
  fetch("http://localhost:8000")
    .then((response) => response.json())
    .then((tables) => {
      const tableSelect = document.getElementById("tableSelect");
      tables.forEach((t) => {
        const option = document.createElement("option");
        option.value = t;
        option.text = t;
        tableSelect.appendChild(option);
      });
      const [t] = tables;
      table = t;
      populateColumnSelect(t);
    })
    .catch((error) => console.error("Error:", error));
}

populateTableSelect();

document.getElementById("tableSelect").addEventListener("change", function () {
  table = this.value;
  // Clear the columnSelect dropdown
  const columnSelect = document.getElementById("columnSelect");
  while (columnSelect.firstChild) {
    columnSelect.removeChild(columnSelect.firstChild);
  }
  populateColumnSelect(table);
  deck.setProps({
    layers: [...layers.slice(0, -1), createH3TileLayer(table, column)],
  });
});

table = document.getElementById("tableSelect").value;
column = document.getElementById("columnSelect").value;

document.getElementById("tableSelect").addEventListener("change", function () {
  table = this.value;
  deck.setProps({
    layers: [...layers.slice(0, -1), createH3TileLayer(table, column)],
  });
});

document.getElementById("columnSelect").addEventListener("change", function () {
  column = this.value;
  deck.setProps({
    layers: [...layers.slice(0, -1), createH3TileLayer(table, column)],
  });
});

const layers = [createH3TileLayer(table, column)];

const map = new maplibregl.Map({
  container: "map",
  style:
    "https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json",
  center: [0.45, 51.47],
  zoom: 3,
  bearing: 0,
  pitch: 0,
});

const deck = new DeckOverlay({
  controller: true,
  layers: layers,
  getTooltip: ({ object }) =>
    object &&
    `${Object.keys(object)[0]}: ${(+Object.values(object)[0]).toFixed(2)}`,
});

map.addControl(deck);
map.addControl(new maplibregl.NavigationControl());
