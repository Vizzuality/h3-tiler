/* eslint-disable react/prop-types */
import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import { H3Map } from "@/components/Map";
import { LayerSelect } from "@/components/Card";

export default function App({}) {
  const [selectedLayer, setSelectedLayer] = useState(null);
  return (
    <div>
      {/*<LayerSelect*/}
      {/*  className="absolute top-5 right-5 z-10"*/}
      {/*  selectedLayer={selectedLayer}*/}
      {/*  setSelectedLayer={setSelectedLayer}*/}
      {/*/>*/}
      <H3Map selectedLayer={selectedLayer}></H3Map>
    </div>
  );
}

export function renderToDOM(container) {
  createRoot(container).render(<App />);
}
