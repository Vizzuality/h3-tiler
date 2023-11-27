import { scaleSequential } from "d3-scale";
import { interpolateViridis } from "d3-scale-chromatic";
import { cellToLatLng } from "h3-js";
import { color } from "d3-color";
import DeckGL from "@deck.gl/react";
import maplibregl from "maplibre-gl";
import H3TileLayer from "h3tile-layer";
import { H3HexagonLayer } from "@deck.gl/geo-layers";
import { ScatterplotLayer } from "@deck.gl/layers";
import { Map } from "react-map-gl";

const INITIAL_VIEW_STATE = {
  longitude: 0,
  latitude: 0,
  zoom: 2,
  maxZoom: 16,
  pitch: 0,
  bearing: 0,
};

const mapStyle =
  "https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json";

export function H3Map({ selectedLayer }) {
  let layers = [];

  if (selectedLayer) {
    const colorscale = scaleSequential()
      .domain([selectedLayer.min_value, selectedLayer.max_value])
      .interpolator(interpolateViridis);

    const maxZoom = selectedLayer.max_res - 5;
    const dataUrl = `http://127.0.0.1:8000/${selectedLayer.h3_table_name}/${selectedLayer.column_name}/{h3index}`;
    layers = [
      new H3TileLayer({
        data: dataUrl,
        minZoom: 0,
        maxZoom: maxZoom,
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
              getFillColor: (d) => {
                let c = color(colorscale(Object.values(d)[0])).rgb();
                return [c.r, c.g, c.b];
              },
              opacity: 0.8,
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
            getFillColor: (d) => {
              let c = color(colorscale(Object.values(d)[0])).rgb();
              return [c.r, c.g, c.b];
            },
            opacity: 0.8,
          });
        },
      }),
    ];
  }

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
