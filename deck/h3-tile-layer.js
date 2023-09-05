import {_Tileset2D as Tileset2D} from '@deck.gl/geo-layers';
import {cellToBoundary, cellToParent, getResolution, polygonToCells} from "h3-js";
import bbox from "@turf/bbox";
import {lineString} from "@turf/helpers";

export class H3Tileset2D extends Tileset2D {

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
        let cells = polygonToCells(polygon, z, true);
        while (cells.length > 30 && z >= 0) {
            z -= 1;
            cells = polygonToCells(polygon, z, true);
        }
        // console.log(z)
        // console.log(cells)
        return cells.map(h3index => ({"h3index": h3index}));
    }

    getTileId({h3index}) {
        console.log(h3index)
        return h3index;
    }

    getTileZoom({h3index}) {
        return getResolution(h3index);
    }

    getParentIndex({h3index}) {
        const res = getResolution(h3index);
        return {"h3index": cellToParent(h3index, res - 1)};
    }

    /** Returns the tile's bounding box */
    getTileMetadata(index) {
        let cell_bbox = bbox(lineString(cellToBoundary(index.h3index, true)));
        // cell_bbox is [minX, minY, maxX, maxY], but we need [west, north, east, south]
        return {bbox: {west: cell_bbox[0], north: cell_bbox[3], east: cell_bbox[2], south: cell_bbox[1]}};
    }
}
