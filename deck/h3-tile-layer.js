import {
  H3HexagonLayer,
  TileLayer,
  _Tileset2D as Tileset2D,
} from "@deck.gl/geo-layers";
import { GeoJsonLayer, ScatterplotLayer } from "@deck.gl/layers";
import bbox from "@turf/bbox";
import bboxPolygon from "@turf/bbox-polygon";
import { lineString } from "@turf/helpers";
import chroma from "chroma-js";
import {
  cellToBoundary,
  cellToLatLng,
  cellToParent,
  edgeLength,
  getResolution,
  latLngToCell,
  originToDirectedEdges,
  polygonToCells,
} from "h3-js";

window.polygonToCells = polygonToCells;

const COLORSCALE = chroma.scale("viridis").domain([0, 1]);

/** Fills the viewport bbox polygon(s) with h3 cells */
function fillViewportBBoxes(bboxes, tileRes) {
  let cells = [];
  for (let bbox of bboxes) {
    const poly = [
      [bbox[0], bbox[1]],
      [bbox[0], bbox[3]],
      [bbox[2], bbox[3]],
      [bbox[2], bbox[1]],
      [bbox[0], bbox[1]],
    ];
    cells = cells.concat(polygonToCells(poly, tileRes, true));
  }
  return cells;
}

/** Splits viewport bounds into two if span is > 180 and adds buffer to include border hexagons.
 * Also clamps viewport bounds to the world bounds [-+180, -+90], which maybe backfires if used in GlobeView
 * */
function makeBufferedBounds(bounds, tileRes) {
  // getHexagonEdgeLengthAvg for a given resolution doesn't have "rads"
  // as a unit option, even that the docs say it does >:(.
  // So will use random edge from the central cell as an edge length proxy since it doesn't need to be exact.
  const medLat = (bounds[1] + bounds[3]) / 2;
  const medLng = (bounds[0] + bounds[2]) / 2;
  const centroidCellEdges = originToDirectedEdges(
    latLngToCell(medLat, medLng, tileRes),
  );
  // largest edge from the center cell of the viewport
  const buffer =
    (Math.max(...centroidCellEdges.map((x) => edgeLength(x, "rads"))) * 180) /
    Math.PI;
  bounds[0] = Math.max(bounds[0] - buffer, -180); // min X
  bounds[1] = Math.max(bounds[1] - buffer, -90); // min Y
  bounds[2] = Math.min(bounds[2] + buffer, 180); // max X
  bounds[3] = Math.min(bounds[3] + buffer, 90); // max Y
  // polygons spanning more than 180 degrees need to be split in two parts to be correctly covered by h3
  // https://github.com/uber/h3-js/issues/180#issuecomment-1652453683
  // So split the bounds in two parts
  if (bounds[2] - bounds[0] > 180) {
    let bounds2 = [...bounds];
    let xSplitPoint = (bounds[2] - bounds[0]) / 2;
    // new min and max X at split point
    bounds[2] -= xSplitPoint;
    bounds2[0] += xSplitPoint;
    return [bounds, bounds2];
  } else {
    return [bounds];
  }
}

class H3Tileset2D extends Tileset2D {
  /** Returns true if the tile is visible in the current viewport
   * FIXME: Should be adapted to h3 tiles. How? no idea...
   * */
  isTileVisible(tile, cullRect) {
    return super.isTileVisible(tile, cullRect);
  }

  /** Returns the tile indices that are needed to cover the viewport
   * It tries to get a sensible number of tiles by computing the h3 resolution
   * that will be used to cover the viewport in h3 cells.
   * If the number of cells is too high,
   * it decreases the resolution until the number of cells is below a threshold.
   * */
  getTileIndices(opts) {
    let tileRes = Math.max(Math.floor(opts.viewport.zoom / 1.7 - 1), 0);

    if (
      typeof opts.minZoom === "number" &&
      Number.isFinite(opts.minZoom) &&
      tileRes < opts.minZoom
    ) {
      if (!opts.extent) {
        return [];
      }

      tileRes = opts.minZoom;
    }

    if (
      typeof opts.maxZoom === "number" &&
      Number.isFinite(opts.maxZoom) &&
      tileRes > opts.maxZoom
    ) {
      tileRes = opts.maxZoom;
    }
    console.log("tileRes, maxZoom", tileRes, opts.maxZoom);

    let bufferedBounds = makeBufferedBounds(opts.viewport.getBounds(), tileRes);
    let cells = fillViewportBBoxes(bufferedBounds, tileRes);
    return cells.map((h3index) => ({ h3index: h3index }));
  }

  getTileId({ h3index }) {
    return h3index;
  }

  getTileZoom({ h3index }) {
    return getResolution(h3index);
  }

  getParentIndex({ h3index }) {
    const res = getResolution(h3index);
    // FIXME: this return raises a type warning in the ide which expects an object like
    //  {x: number, y: number, z: number} and I don't know how to patch this type to {h3index: string}
    return { h3index: cellToParent(h3index, res - 1) };
  }

  /** Returns the tile's bounding box
   * Needed for setting BoundingBox in Tile2DHeader (aka tile param in getTileData of TileLayer)
   * */
  getTileMetadata(index) {
    let cell_bbox = bbox(lineString(cellToBoundary(index.h3index, true)));
    // bbox is [minX, minY, maxX, maxY]
    return {
      bbox: {
        west: cell_bbox[0],
        north: cell_bbox[3],
        east: cell_bbox[2],
        south: cell_bbox[1],
      },
    };
  }
}

/** Debug layer that renders the h3 hex tiles as polygons.
 * Help to inspect which tiles are being requested and at which resolution
 * */
export const DebugH3TileLayer = new TileLayer({
  TilesetClass: H3Tileset2D,
  id: "tile-h3s-boundaries",
  getTileData: (tile) => {
    return [tile.index];
  },
  minZoom: 0,
  maxZoom: 4,
  renderSubLayers: (props) => {
    // console.log(props)
    return new H3HexagonLayer({
      id: props.id,
      data: props.data,
      highPrecision: "auto",
      pickable: false,
      wireframe: true,
      filled: true,
      extruded: false,
      stroked: true,
      getHexagon: (d) => d.h3index,
      getFillColor: [0, 0, 255, 0],
      getLineColor: [0, 0, 255, 255],
      lineWidthUnits: "pixels",
      getLineWidth: 2,
    });
  },
});

/** Debug layer for the tile's bounding boxes */
export const DebugH3BBoxTileLayer = new TileLayer({
  TilesetClass: H3Tileset2D,
  id: "tile-h3s-bboxes",
  getTileData: (tile) => {
    return bboxPolygon(
      bbox(lineString(cellToBoundary(tile.index.h3index, true))),
    );
  },
  minZoom: 0,
  maxZoom: 20,
  renderSubLayers: (props) => {
    return new GeoJsonLayer({
      id: props.id,
      data: props.data,
      getPolygon: (d) => d.geometry.coordinates[0],
      pickable: false,
      stroked: true,
      filled: false,
      wireframe: true,
      lineWidthMinPixels: 2,
      getLineColor: [255, 0, 0],
      getLineWidth: 2,
    });
  },
});

export function createH3TileLayer(table = "", column = "value", maxZoom = 12) {
  return new TileLayer({
    TilesetClass: H3Tileset2D,
    id: "tile-h3s",
    data: `http://127.0.0.1:8000/${table}/${column}/{h3index}`,
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
  });
}

export const H3TileLayer = createH3TileLayer();
