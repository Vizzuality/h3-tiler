import { Deck } from "@deck.gl/core";
import { GeoJsonLayer } from "@deck.gl/layers";
import {
  DebugH3BBoxTileLayer,
  DebugH3TileLayer,
  H3TileLayer,
  createH3TileLayer,
} from "./h3-tile-layer";
import { collectionOf } from "@turf/invariant";

const COUNTRIES =
  "https://d2ad6b4ur7yvpq.cloudfront.net/naturalearth-3.3.0/ne_50m_admin_0_scale_rank.geojson"; //eslint-disable-line

const INITIAL_VIEW_STATE = {
  latitude: 51.47,
  longitude: 0.45,
  zoom: 3,
  bearing: 0,
  pitch: 0,
};

fetch("http://localhost:8000")
  .then((response) => response.json())
  .then((tables) => {
    const tableSelect = document.getElementById("tableSelect");
    tables.forEach((table) => {
      const option = document.createElement("option");
      option.value = table;
      option.text = table;
      tableSelect.appendChild(option);
    });
  })
  .catch((error) => console.error("Error:", error));

document.getElementById("tableSelect").addEventListener("change", function () {
  let table = this.value;

  // Clear the columnSelect dropdown
  const columnSelect = document.getElementById("columnSelect");
  while (columnSelect.firstChild) {
    columnSelect.removeChild(columnSelect.firstChild);
  }

  // Fetch the columns for the new table and populate the columnSelect dropdown
  fetch(`http://localhost:8000/${table}`)
    .then((response) => response.json())
    .then((columns) => {
      columns.forEach((column) => {
        const option = document.createElement("option");
        option.value = column;
        option.text = column;
        if (column === "value") {
          option.selected = true;
        }
        columnSelect.appendChild(option);
      });
    })
    .catch((error) => console.error("Error:", error));

  deck.setProps({
    layers: [...layers.slice(0, -1), createH3TileLayer(table, column)],
  });
});

let table = document.getElementById("tableSelect").value;
let column = document.getElementById("columnSelect").value;

const layers = [
  new GeoJsonLayer({
    id: "base-map",
    data: COUNTRIES,
    stroked: true,
    filled: true,
    lineWidthMinPixels: 2,
    opacity: 0.4,
    getLineColor: [60, 60, 60],
    getFillColor: [200, 200, 200],
  }),
  createH3TileLayer(table, column),
];

const deck = new Deck({
  initialViewState: INITIAL_VIEW_STATE,
  controller: true,
  layers: layers,
  getTooltip: ({ object }) =>
    object &&
    `${Object.keys(object)[0]}: ${(+Object.values(object)[0]).toFixed(2)}`,
});

document.getElementById("tableSelect").addEventListener("change", function () {
  table = this.value;
  deck.setProps({
    layers: [...layers.slice(0, -1), createH3TileLayer(table, column)],
  });
});

document.getElementById("columnSelect").addEventListener("change", function () {
  let column = this.value;
  deck.setProps({
    layers: [...layers.slice(0, -1), createH3TileLayer(table, column)],
  });
});
