import { H3HexagonLayer } from "@deck.gl/geo-layers";
import DeckGL from "@deck.gl/react";
import { ArrowLoader } from "@loaders.gl/arrow";
import { load } from "@loaders.gl/core";
import { color } from "d3-color";
import { scaleSequential } from "d3-scale";
import { interpolateViridis } from "d3-scale-chromatic";
import H3TileLayer, { DebugH3TileLayer } from "h3tile-layer";
import maplibregl from "maplibre-gl";
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
  const colorscale = scaleSequential()
    .domain([1, 5])
    // .domain([selectedLayer.min_value, selectedLayer.max_value])
    .interpolator(interpolateViridis);

  // const maxZoom = selectedLayer.max_res - 5;
  const maxZoom = 4;
  let layers = [
    new H3TileLayer({
      id: "tile-h3s",
      data: "https://dev.api.amazonia360.dev-vizzuality.com/grid/tile/{h3index}",
      getTileData: (tile) => {
        return load(tile.url, ArrowLoader, {
          arrow: { shape: "object-row-table" },
        }).then((data) => {
          return data.data;
        });
      },
      onTileError: () => {},
      minZoom: 0,
      maxZoom: maxZoom,
      maxRequests: 10, // max simultaneous requests. Set 0 for unlimited
      maxCacheSize: 300, // max number of tiles to keep in the cache
      renderSubLayers: (props) => {
        // For zoom < 1 (~whole world view), render a scatterplot layer instead of the hexagon layer
        // It is faster to render points than hexagons (is it?) when there are many cells.
        // if (props.tile.zoom < 1) {
        //   return new ScatterplotLayer({
        //     id: props.id,
        //     data: props.data,
        //     pickable: true,
        //     radiusUnits: "meters",
        //     getRadius: 9854, // is the radius of a h3 cell at resolution 5 in meters
        //     getPosition: (d) =>
        //       cellToLatLng(BigInt(d.cell).toString(16)).reverse(),
        //     getFillColor: (d) => {
        //       let c = color(colorscale(d.fire)).rgb();
        //       return [c.r, c.g, c.b];
        //     },
        //     opacity: 0.8,
        //   });
        // }
        return new H3HexagonLayer({
          id: props.id,
          data: props.data,
          highPrecision: "auto",
          pickable: true,
          wireframe: false,
          filled: true,
          extruded: false,
          stroked: false,
          // getLineColor: [255, 255, 255, 255],
          // getLineWidth:  10,
          coverage: 1,
          getHexagon: (d) => {
            const res = BigInt(d.cell);
            return res.toString(16);
          },
          getFillColor: (d) => {
            let c = color(colorscale(d.fire)).rgb();
            return [c.r, c.g, c.b];
          },
          opacity: 1,
        });
      },
    }),
    DebugH3TileLayer,
  ];
  // const view = new GlobeView()
  return (
    <DeckGL
      layers={layers}
      initialViewState={INITIAL_VIEW_STATE}
      controller={true}
      getTooltip={({ object }) =>
        object && `id: ${object.cell}\n value: ${object.fire}`
      }
      // views={view}
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
