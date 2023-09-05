import {_Tileset2D as Tileset2D, H3HexagonLayer, TileLayer} from '@deck.gl/geo-layers';
import {cellToBoundary, cellToParent, getResolution, polygonToCells} from "h3-js";
import bbox from "@turf/bbox";
import {lineString} from "@turf/helpers";
import chroma from "chroma-js";

const colorScale = chroma.scale("OrRd").domain([0, 135]);

class H3Tileset2D extends Tileset2D {

    isTileVisible(tile, cullRect) {
        if (!tile.isVisible) {
            return false;
        }
        if (cullRect && this._viewport) {
            const boundsArr = this._getCullBounds({
                viewport: this._viewport,
                z: this._zRange,
                cullRect
            });
            const {
                bbox
            } = tile;
            for (const [minX, minY, maxX, maxY] of boundsArr) {
                let overlaps;
                if ('west' in bbox) {
                    overlaps = bbox.west < maxX && bbox.east > minX && bbox.south < maxY && bbox.north > minY;
                } else {
                    const y0 = Math.min(bbox.top, bbox.bottom);
                    const y1 = Math.max(bbox.top, bbox.bottom);
                    overlaps = bbox.left < maxX && bbox.right > minX && y0 < maxY && y1 > minY;
                }
                if (overlaps) {
                    return true;
                }
            }
            return false;
        }
        return true;
    }

    /** Returns the tile indices that are needed to cover the viewport
     * It tries to get a sensible number of tiles by computing the h3 resolution
     * that will be used to cover the viewport in h3 cells.
     * If the number of cells is too high,
     * it decreases the resolution until the number of cells is below a threshold.
     * */
    getTileIndices(opts) {
        // get z level from viewport original implementation
        let z = Math.min(Math.max(Math.floor(opts.viewport.zoom) - 2, 0), 4);
        // [minX, minY, maxX, maxY]
        const bounds = opts.viewport.getBounds();
        const polygon = [
            [bounds[0], bounds[1]],
            [bounds[0], bounds[3]],
            [bounds[2], bounds[3]],
            [bounds[2], bounds[1]],
            [bounds[0], bounds[1]]
        ]
        // fill the viewport polygon with h3 cells
        let cells = polygonToCells(polygon, z, true);
        while (cells.length > 30 && z >= 0) {
            z -= 1;
            cells = polygonToCells(polygon, z, true);
        }
        // console.log(z)
        console.log(cells)
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
        // FIXME: this return raises a type warning in the ide which expects and object like
        // {x: number, y: number, z: number} and I don't know how to patch he this type to a h3index
        return {"h3index": cellToParent(h3index, res - 1)};
    }

    /** Returns the tile's bounding box
     * Needed for setting BoundingBox in Tile2DHeader (aka tile param)
     * */
    getTileMetadata(index) {
        let cell_bbox = bbox(lineString(cellToBoundary(index.h3index, true)));
        // cell_bbox is [minX, minY, maxX, maxY], but we need [west, north, east, south]
        return {bbox: {west: cell_bbox[0], north: cell_bbox[3], east: cell_bbox[2], south: cell_bbox[1]}};
    }
}


export const DebugH3TileLayer = new TileLayer({
    TilesetClass: H3Tileset2D,
    id: 'tile-h3s-boundaries',
    getTileData: tile => {
        return {h3index: tile.index}
    },
    minZoom: 0,
    maxZoom: 20,
    tileSize: 512,  // FIXME: tileSize does not make any sense for h3 hex tiles. Should be removed.
    maxRequests: 10,  // max simultaneous requests. Set 0 for unlimited
    renderSubLayers: props => {
        const h3Indexes = props.data; // List of H3 indexes for the tile
        return new H3HexagonLayer({
            id: `h3-boundaries`,
            data: h3Indexes,
            highPrecision: 'auto',
            pickable: true,
            wireframe: true,
            filled: false,
            extruded: false,
            stroked: true,
            getHexagon: d => d.h3index,
            // getFillColor: d => colorScale(d.value).rgb(),
            getLineColor: [0, 0, 255, 255],
            lineWidthUnits: 'pixels',
            lineWidth: 2,
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
        const h3Indexes = props.data; // List of H3 indexes for the tile
        return new H3HexagonLayer({
            id: `h3-layer`,
            data: h3Indexes,
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
