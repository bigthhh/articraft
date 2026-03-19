import { type JSX } from "react";
import type * as THREE from "three";

import { SceneCanvas } from "@/components/viewer3d/SceneCanvas";
import type { RenderOptions } from "@/components/viewer3d/useRenderOptions";
import type { UrdfSpec } from "@/components/viewer3d/urdf-parser";

interface ViewportPanelProps {
  baseFileUrl: string | null;
  assetRevisionKey: string | null;
  selectionKey: string | null;
  renderOptions: RenderOptions;
  onUrdfSpecChange: (spec: UrdfSpec | null, jointNodes: Map<string, THREE.Object3D> | null) => void;
}

export function ViewportPanel({
  baseFileUrl,
  assetRevisionKey,
  selectionKey,
  renderOptions,
  onUrdfSpecChange,
}: ViewportPanelProps): JSX.Element {
  // Map from useRenderOptions format to RenderOptionsPanel format for SceneCanvas
  const sceneRenderOptions = {
    showEdges: renderOptions.showEdges,
    showGrid: renderOptions.showGrid,
    showCollisions: renderOptions.showCollisions,
    doubleSided: renderOptions.doubleSided,
    environmentLighting: renderOptions.envLighting,
    autoAnimate: renderOptions.autoAnimate,
    showJointOverlay: renderOptions.showJointOverlay,
  };

  return (
    <section className="relative h-full w-full min-w-0 overflow-hidden bg-[var(--surface-2)]">
      <SceneCanvas
        baseFileUrl={baseFileUrl}
        assetRevisionKey={assetRevisionKey}
        selectionKey={selectionKey}
        renderOptions={sceneRenderOptions}
        onUrdfSpecChange={onUrdfSpecChange}
      />
    </section>
  );
}
