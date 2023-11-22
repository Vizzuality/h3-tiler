/* eslint-disable react/prop-types */
import { H3HexagonLayer } from "@deck.gl/geo-layers";
import { ScatterplotLayer } from "@deck.gl/layers";
import DeckGL from "@deck.gl/react";
import chroma from "chroma-js";
import { cellToLatLng } from "h3-js";
import maplibregl from "maplibre-gl";
import React from "react";
import { createRoot } from "react-dom/client";
import { Map } from "react-map-gl";

import H3TileLayer from "h3tile-layer";

const INITIAL_VIEW_STATE = {
  longitude: -74,
  latitude: 40.7,
  zoom: 11,
  maxZoom: 16,
  pitch: 0,
  bearing: 0,
};

const COLORSCALE = chroma.scale("viridis").domain([0, 1]);

export default function App({
  mapStyle = "https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json",
}) {
  const layers = [
    new H3TileLayer({
      data: `http://127.0.0.1:8000/h3_lossyear_area/value/{h3index}`,
      minZoom: 0,
      maxZoom: 3,
      maxRequests: 10, // max simultaneous requests. Set 0 for unlimited
      maxCacheSize: 300, // max number of tiles to keep in the cache
      renderSubLayers: (props) => {
        // For zoom < 1 (~whole world view), render a scatterplot layer instead of the hexagon layer
        // It is faster to render points than hexagons (is it?) when there are many cells.
        if (props.tile.zoom < 1) {
          return new ScatterplotLayer({
            id: props.id,
            data: props.data,
            pickable: true,
            radiusUnits: "meters",
            getRadius: 9854, // is the radius of a h3 cell at resolution 5 in meters
            getPosition: (d) => cellToLatLng(Object.keys(d)[0]).reverse(),
            getFillColor: (d) => COLORSCALE(Object.values(d)[0]).rgb(),
          });
        }
        return new H3HexagonLayer({
          id: props.id,
          data: props.data,
          highPrecision: "auto",
          pickable: true,
          wireframe: false,
          filled: true,
          extruded: false,
          stroked: false,
          getHexagon: (d) => Object.keys(d)[0],
          getFillColor: (d) => COLORSCALE(Object.values(d)[0]).rgb(),
        });
      },
    }),
  ];

  return (
    <DeckGL
      layers={layers}
      initialViewState={INITIAL_VIEW_STATE}
      controller={true}
    >
      <Map
        reuseMaps
        mapLib={maplibregl}
        mapStyle={mapStyle}
        preventStyleDiffing={true}
      />
    </DeckGL>
  );
}

export function renderToDOM(container) {
  createRoot(container).render(<App />);
}
