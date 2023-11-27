// vite.config.js
export default {
  build: {
    lib: {
      entry: "src/h3tile-layer.js",
      name: "H3TileLayer",
    },
    rollupOptions: {
      external: [
        "@deck.gl/geo-layers",
        "@deck.gl/layers",
        "@turf/bbox",
        "@turf/bbox-polygon",
        "@turf/helpers",
        "h3-js",
      ],
      output: {
        globals: {
          "@deck.gl/geo-layers": "GeoLayers",
          "@deck.gl/layers": "Layers",
          "@turf/bbox": "Bbox",
          "@turf/bbox-polygon": "BboxPolygon",
          "@turf/helpers": "Helpers",
          "h3-js": "H3",
        },
      },
    },
  },
};
