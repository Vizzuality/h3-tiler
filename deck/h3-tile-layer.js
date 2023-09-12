import {_Tileset2D as Tileset2D, H3HexagonLayer, TileLayer} from '@deck.gl/geo-layers';
import {cellToBoundary, cellToParent, getResolution, polygonToCells} from "h3-js";
import bbox from "@turf/bbox";
import {lineString} from "@turf/helpers";
import chroma from "chroma-js";
import {GeoJsonLayer} from "@deck.gl/layers";
import bboxPolygon from "@turf/bbox-polygon";

window.polygonToCells = polygonToCells;

const COLORSCALE = chroma.scale("viridis").domain([0, 130]);

/** Fills the viewport bbox polygon(s) with h3 cells */
function fillBBoxes(bboxes, z) {
    let cells = [];
    for (let bbox of bboxes) {
        const poly = [
            [bbox[0], bbox[1]],
            [bbox[0], bbox[3]],
            [bbox[2], bbox[3]],
            [bbox[2], bbox[1]],
            [bbox[0], bbox[1]]
        ]
        cells = cells.concat(polygonToCells(poly, z, true));
    }
    return cells;
}

/** Prepares the viewport bounds to be correct for filling with h3 cells */
function prepareBounds(bounds) {
    // Add a buffer with x % of the larger axis,
    // so the hexagons which centroid lays out of the viewport are also included.
    // Also, we need to clamp the bounds to the world boundaries.
    const buffer = Math.max(bounds[2] - bounds[0], bounds[3] - bounds[1]) * 0.1;
    bounds[0] = Math.max(bounds[0] - buffer, -180);
    bounds[1] = Math.max(bounds[1] - buffer, -90);
    bounds[2] = Math.min(bounds[2] + buffer, 180);
    bounds[3] = Math.min(bounds[3] + buffer, 90);
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
        let tileRes = Math.min(Math.max(Math.floor(opts.viewport.zoom) - 3, 0), 3);
        let bounds = prepareBounds(opts.viewport.getBounds());
        let cells = fillBBoxes(bounds, tileRes);
        // TODO: The resolution should be computed with a sensible algo from the viewport size,
        //  and not fixed on the fly with a magic number to limit the number of cells.
        while (cells.length > 50 && tileRes > 0) {
            cells = fillBBoxes(bounds, tileRes);
            tileRes -= 1;
        }
        console.log("h3 resolution: " + tileRes + "\n zoom: " + opts.viewport.zoom)
        return cells.map(h3index => ({"h3index": h3index}));
    }

    getTileId({h3index}) {
        return h3index;
    }

    getTileZoom({h3index}) {
        return getResolution(h3index);
    }

    getParentIndex({h3index}) {
        const res = getResolution(h3index);
        // FIXME: this return raises a type warning in the ide which expects an object like
        //  {x: number, y: number, z: number} and I don't know how to patch this type to {h3index: string}
        return {"h3index": cellToParent(h3index, res - 1)};
    }

    /** Returns the tile's bounding box
     * Needed for setting BoundingBox in Tile2DHeader (aka tile param in getTileData of TileLayer)
     * */
    getTileMetadata(index) {
        let cell_bbox = bbox(lineString(cellToBoundary(index.h3index, true)));
        // bbox is [minX, minY, maxX, maxY]
        return {bbox: {west: cell_bbox[0], north: cell_bbox[3], east: cell_bbox[2], south: cell_bbox[1]}};
    }
}


/** Debug layer that renders the h3 hex tiles as polygons.
 * Help to inspect which tiles are being requested and at which resolution
 * */
export const DebugH3TileLayer = new TileLayer({
    TilesetClass: H3Tileset2D,
    id: 'tile-h3s-boundaries',
    getTileData: tile => {
        return [tile.index]
    },
    minZoom: 0,
    maxZoom: 20,
    renderSubLayers: props => {
        // console.log(props)
        return new H3HexagonLayer({
            id: props.id,
            data: props.data,
            highPrecision: 'auto',
            pickable: true,
            wireframe: true,
            filled: true,
            extruded: false,
            stroked: true,
            getHexagon: d => d.h3index,
            getFillColor: d => [0, 0, 255, 0],
            getLineColor: [0, 0, 255, 255],
            lineWidthUnits: 'pixels',
            getLineWidth: 2
        });
    }
})

/** Debug layer for the tile's bounding boxes */
export const DebugH3BBoxTileLayer = new TileLayer({
    TilesetClass: H3Tileset2D,
    id: 'tile-h3s-bboxes',
    getTileData: tile => {
        return bboxPolygon(bbox(lineString(cellToBoundary(tile.index.h3index, true))))
    },
    minZoom: 0,
    maxZoom: 20,
    renderSubLayers: props => {
        return new GeoJsonLayer({
            id: props.id,
            data: props.data,
            getPolygon: d => d.geometry.coordinates[0],
            pickable: false,
            stroked: true,
            filled: false,
            wireframe: true,
            lineWidthMinPixels: 2,
            getLineColor: [255, 0, 0],
            getLineWidth: 2
        });
    }
})


export const H3TileLayer = new TileLayer({
    TilesetClass: H3Tileset2D,
    id: 'tile-h3s',
    data: 'http://127.0.0.1:8000/h3index/{h3index}',
    minZoom: 0,
    maxZoom: 20,
    tileSize: 512,  // FIXME: tileSize does not make any sense for h3 hex tiles. Should be removed.
    maxRequests: 6,  // max simultaneous requests. Set 0 for unlimited
    maxCacheSize: 300,  // max number of tiles to keep in the cache
    renderSubLayers: props => {
        return new H3HexagonLayer({
            id: props.id,
            data: props.data,
            highPrecision: 'auto',
            pickable: true,
            wireframe: false,
            filled: true,
            extruded: false,
            stroked: false,
            getHexagon: d => d.h3index,
            getFillColor: d => COLORSCALE(d.value).rgb(),
            getLineColor: [0, 0, 255, 255],
            lineWidthUnits: 'pixels',
            lineWidth: 1,
        });
    }
})
