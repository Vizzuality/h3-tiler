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
const COLORSCALE = scaleSequential()
  .domain([0, 1])
  .interpolator(interpolateViridis);

const mapStyle =
  "https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json";

export function H3Map() {
  const layers = [
    new H3TileLayer({
      data: `http://127.0.0.1:8000/h3_lossyear_area/value/{h3index}`,
      minZoom: 0,
      maxZoom: 6,
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
              let c = color(COLORSCALE(Object.values(d)[0])).rgb();
              return [c.r, c.g, c.b];
            },
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
            let c = color(COLORSCALE(Object.values(d)[0])).rgb();
            return [c.r, c.g, c.b];
          },
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
