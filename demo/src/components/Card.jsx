import { cn } from "@/lib/utils";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import React, { useEffect, useState } from "react";

export function LayerSelect({
  className,
  selectedLayer,
  setSelectedLayer,
  ...props
}) {
  const [layers, setLayers] = useState([]);

  useEffect(() => {
    fetch("http://localhost:8000/meta")
      .then((response) => response.json())
      .then((data) => {
        // setLayers(data.map((layer, i) => {
        //   return { ...layer, selected: i === 0 }
        // }))
        setLayers(data);
      });
  }, []);

  const handleSwitchChange = (layer) => {
    const updatedLayers = layers.map((l) => {
      if (l === layer) {
        return { ...l, selected: true };
      } else {
        return { ...l, selected: false };
      }
    });
    setLayers(updatedLayers);
    setSelectedLayer(layer);
  };

  return (
    <Card className={cn("w-[380px]", className)} {...props}>
      <CardHeader>
        <CardTitle>H3 tile layers</CardTitle>
        <CardDescription>Select layer to show</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div>
          {layers.map((layer, index) => (
            <div
              key={index}
              className=" flex items-center justify-between space-x-10 p-4"
            >
              <div className="space-y-1">
                <p className="text-sm font-medium leading-none">{layer.name}</p>
                <p className="text-sm text-muted-foreground">
                  {layer.description}
                </p>
              </div>
              <Switch
                checked={layer.selected}
                onCheckedChange={() => handleSwitchChange(layer)}
              />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
