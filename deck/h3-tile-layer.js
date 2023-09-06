import {_Tileset2D as Tileset2D, H3HexagonLayer, TileLayer} from '@deck.gl/geo-layers';
import {cellToBoundary, cellToParent, getResolution, polygonToCells} from "h3-js";
import bbox from "@turf/bbox";
import {lineString} from "@turf/helpers";
import chroma from "chroma-js";


class H3Tileset2D extends Tileset2D {

    /** Returns true if the tile is visible in the current viewport
     * FIXME: This is a copy of the original implementation in deck.gl
     * Should be adapted to h3 hex tiles. how? no idea...
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
        // get z level from viewport original implementation
        let z = Math.min(Math.max(Math.floor(opts.viewport.zoom) - 3, 1), 4);
        // [minX, minY, maxX, maxY]
        let bounds = opts.viewport.getBounds();
        const buffer = Math.max(bounds[2] - bounds[0], bounds[3] - bounds[1]) * 0.05;
        // Add a buffer of 10% to the viewport bounds so the border tiles are also included
        bounds[0] -= buffer;
        bounds[1] -= buffer;
        bounds[2] += buffer;
        bounds[3] += buffer;
        const viewportPolygon = [
            [bounds[0], bounds[1]],
            [bounds[0], bounds[3]],
            [bounds[2], bounds[3]],
            [bounds[2], bounds[1]],
            [bounds[0], bounds[1]]
        ]
        // fill the viewport polygon with h3 cells
        let cells = polygonToCells(viewportPolygon, z, true);
        while (cells.length > 150 && z >= 0) {
            cells = polygonToCells(viewportPolygon, z, true);
            z -= 1;
        }
        console.log(cells.length)
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
        //  {x: number, y: number, z: number} and I don't know how to patch he this type to a h3index
        return {"h3index": cellToParent(h3index, res - 1)};
    }

    /** Returns the tile's bounding box
     * Needed for setting BoundingBox in Tile2DHeader (aka tile param)
     * */
    getTileMetadata(index) {
        let cell_bbox = bbox(lineString(cellToBoundary(index.h3index, true)));
        // bbox is [minX, minY, maxX, maxY]
        return {bbox: {west: cell_bbox[0], north: cell_bbox[3], east: cell_bbox[2], south: cell_bbox[1]}};
    }
}

const colorScale = chroma.scale("Reds").domain([0, 135]);

/** Debug layer that renders the h3 hex tiles as wireframes
 * and helps to inspect which tiles are being requested and at which resolution
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
            lineWidth: 20,
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
    maxRequests: 10,  // max simultaneous requests. Set 0 for unlimited
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
            getFillColor: d => colorScale(d.value).rgb(),
            getLineColor: [0, 0, 255, 255],
            lineWidthUnits: 'pixels',
            lineWidth: 1,
        });
    }
})
