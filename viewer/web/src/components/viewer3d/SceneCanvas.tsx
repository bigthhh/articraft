import { useRef, useEffect, type JSX } from 'react';
import * as THREE from 'three';
import { useThreeScene } from './useThreeScene';
import { useUrdfLoader } from './useUrdfLoader';
import { createEdgeLines } from './materials';
import { createEnvironmentMap } from './lighting';
import { attachJointOverlay, disposeOverlayObjects } from './joint-overlay';
import type { RenderOptions } from '@/components/inspector/RenderOptionsPanel';
import { updateUrlSearchParams } from '@/lib/url';
import type { UrdfSpec } from './urdf-parser';

const CAMERA_QUERY_PARAM = 'cam';
const SEGMENTATION_PALETTE = [
  '#ff5a36',
  '#00b3ff',
  '#ffd400',
  '#16c47f',
  '#ff2f92',
  '#7c5cff',
  '#ff8a00',
  '#00c2a8',
  '#ff6b6b',
  '#145af2',
  '#c4ff0e',
  '#ff3d77',
] as const;
const SEGMENTATION_SNAPSHOT_KEY = '__articraftSegmentColorSnapshot__';

type MaterialWithColor = THREE.Material & {
  color?: THREE.Color;
  emissive?: THREE.Color;
  map?: THREE.Texture | null;
  emissiveMap?: THREE.Texture | null;
  metalness?: number;
  roughness?: number;
};

type SegmentMaterialSnapshot = {
  color?: THREE.Color;
  emissive?: THREE.Color;
  map?: THREE.Texture | null;
  emissiveMap?: THREE.Texture | null;
  metalness?: number;
  roughness?: number;
  transparent: boolean;
  opacity: number;
};

function segmentColorForIndex(index: number): THREE.Color {
  const base = new THREE.Color(SEGMENTATION_PALETTE[index % SEGMENTATION_PALETTE.length]);
  const hueOffset = Math.floor(index / SEGMENTATION_PALETTE.length) * 0.07;
  return base.offsetHSL(hueOffset, 0.06, 0);
}

function storeSegmentMaterialSnapshot(material: MaterialWithColor): void {
  if (material.userData[SEGMENTATION_SNAPSHOT_KEY]) {
    return;
  }

  material.userData[SEGMENTATION_SNAPSHOT_KEY] = {
    color: material.color?.clone(),
    emissive: material.emissive?.clone(),
    map: material.map ?? null,
    emissiveMap: material.emissiveMap ?? null,
    metalness: material.metalness,
    roughness: material.roughness,
    transparent: material.transparent,
    opacity: material.opacity,
  } satisfies SegmentMaterialSnapshot;
}

function applySegmentColor(material: MaterialWithColor, color: THREE.Color): void {
  storeSegmentMaterialSnapshot(material);

  if (material.color) {
    material.color.copy(color);
  }
  if (material.emissive) {
    material.emissive.setRGB(0.06, 0.06, 0.06);
  }
  if ('map' in material) {
    material.map = null;
  }
  if ('emissiveMap' in material) {
    material.emissiveMap = null;
  }
  if ('metalness' in material && typeof material.metalness === 'number') {
    material.metalness = 0.14;
  }
  if ('roughness' in material && typeof material.roughness === 'number') {
    material.roughness = 0.72;
  }
  material.transparent = false;
  material.opacity = 1;
  material.needsUpdate = true;
}

function restoreSegmentMaterial(material: MaterialWithColor): void {
  const snapshot = material.userData[SEGMENTATION_SNAPSHOT_KEY] as SegmentMaterialSnapshot | undefined;
  if (!snapshot) {
    return;
  }

  if (material.color && snapshot.color) {
    material.color.copy(snapshot.color);
  }
  if (material.emissive) {
    if (snapshot.emissive) {
      material.emissive.copy(snapshot.emissive);
    } else {
      material.emissive.setRGB(0, 0, 0);
    }
  }
  if ('map' in material) {
    material.map = snapshot.map ?? null;
  }
  if ('emissiveMap' in material) {
    material.emissiveMap = snapshot.emissiveMap ?? null;
  }
  if ('metalness' in material && typeof snapshot.metalness === 'number') {
    material.metalness = snapshot.metalness;
  }
  if ('roughness' in material && typeof snapshot.roughness === 'number') {
    material.roughness = snapshot.roughness;
  }
  material.transparent = snapshot.transparent;
  material.opacity = snapshot.opacity;
  material.needsUpdate = true;
  delete material.userData[SEGMENTATION_SNAPSHOT_KEY];
}

function withMeshMaterials(
  mesh: THREE.Mesh,
  visit: (material: MaterialWithColor) => void,
): void {
  const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
  for (const material of materials) {
    if (material) {
      visit(material as MaterialWithColor);
    }
  }
}

export interface SceneCanvasProps {
  baseFileUrl: string | null;
  persistedRecordId: string | null;
  assetRevisionKey: string | null;
  selectionKey: string | null;
  renderOptions: RenderOptions;
  onUrdfSpecChange?: (spec: UrdfSpec | null, jointNodes: Map<string, THREE.Object3D> | null) => void;
}

export function SceneCanvas({
  baseFileUrl,
  persistedRecordId,
  assetRevisionKey,
  selectionKey,
  renderOptions,
  onUrdfSpecChange,
}: SceneCanvasProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const isStagingSelection = selectionKey?.startsWith("staging:") ?? false;

  const { scene, camera, renderer, controls, gridGroup, axisGroup, sceneReady } = useThreeScene(containerRef);
  const { urdfSpec, jointNodes, jointFrames, loading, error } = useUrdfLoader(
    baseFileUrl,
    persistedRecordId,
    assetRevisionKey,
    scene,
    camera,
    controls,
    gridGroup,
    axisGroup,
  );

  useEffect(() => {
    onUrdfSpecChange?.(urdfSpec, jointNodes);
  }, [urdfSpec, jointNodes, onUrdfSpecChange]);

  useEffect(() => {
    updateUrlSearchParams((params) => {
      params.delete(CAMERA_QUERY_PARAM);
    });
  }, []);

  const edgeLinesRef = useRef<THREE.LineSegments[]>([]);
  const envMapRef = useRef<THREE.Texture | null>(null);
  const jointOverlayRef = useRef<THREE.Object3D[]>([]);
  const isStagingBuffering = isStagingSelection && error?.startsWith("Failed to fetch URDF: 404");

  // Show/hide grid
  useEffect(() => {
    if (gridGroup) {
      gridGroup.visible = renderOptions.showGrid;
    }
  }, [gridGroup, renderOptions.showGrid]);

  // Show edges
  useEffect(() => {
    if (!scene) return;

    for (const line of edgeLinesRef.current) {
      line.parent?.remove(line);
      line.geometry.dispose();
      (line.material as THREE.Material).dispose();
    }
    edgeLinesRef.current = [];

    if (!renderOptions.showEdges || renderOptions.showCollisions) return;

    const robot = scene.getObjectByName('__articraft_robot__');
    if (!robot) return;

    const newLines: THREE.LineSegments[] = [];
    robot.traverse((obj) => {
      if (obj instanceof THREE.Mesh && obj.geometry && obj.userData.articraftVisual === true && obj.visible) {
        const edges = createEdgeLines(obj.geometry);
        obj.add(edges);
        newLines.push(edges);
      }
    });
    edgeLinesRef.current = newLines;
  }, [scene, renderOptions.showEdges, renderOptions.showCollisions, urdfSpec]);

  // Double-sided materials
  useEffect(() => {
    if (!scene) return;
    const robot = scene.getObjectByName('__articraft_robot__');
    if (!robot) return;

    robot.traverse((obj) => {
      if (obj instanceof THREE.Mesh) {
        const mat = obj.material;
        const side = obj.userData.articraftCollision === true || renderOptions.doubleSided
          ? THREE.DoubleSide
          : THREE.FrontSide;
        if (Array.isArray(mat)) {
          for (const m of mat) {
            m.side = side;
            m.needsUpdate = true;
          }
        } else if (mat) {
          mat.side = side;
          mat.needsUpdate = true;
        }
      }
    });
  }, [scene, renderOptions.doubleSided, urdfSpec]);

  // Environment lighting
  useEffect(() => {
    if (!scene || !renderer) return;

    if (renderOptions.environmentLighting) {
      if (!envMapRef.current) {
        envMapRef.current = createEnvironmentMap(renderer);
      }
      scene.environment = envMapRef.current;
    } else {
      scene.environment = null;
    }
  }, [scene, renderer, renderOptions.environmentLighting]);

  // Show collisions
  useEffect(() => {
    if (!scene) return;
    const robot = scene.getObjectByName('__articraft_robot__');
    if (!robot) return;

    robot.traverse((obj) => {
      if (obj.userData.articraftVisual === true) {
        obj.visible = !renderOptions.showCollisions;
      }
      if (obj.userData.articraftCollision === true) {
        obj.visible = renderOptions.showCollisions;
      }
    });
  }, [scene, renderOptions.showCollisions, urdfSpec]);

  useEffect(() => {
    if (!scene || !urdfSpec) {
      return;
    }

    const robot = scene.getObjectByName('__articraft_robot__');
    if (!robot) {
      return;
    }

    for (const [index, link] of urdfSpec.links.entries()) {
      const linkGroup = robot.getObjectByName(`link:${link.name}`);
      if (!linkGroup) {
        continue;
      }

      const linkColor = segmentColorForIndex(index);
      linkGroup.traverse((obj) => {
        if (!(obj instanceof THREE.Mesh) || obj.userData.articraftVisual !== true) {
          return;
        }

        withMeshMaterials(obj, (material) => {
          if (renderOptions.showSegmentColors) {
            applySegmentColor(material, linkColor);
          } else {
            restoreSegmentMaterial(material);
          }
        });
      });
    }

    return () => {
      for (const link of urdfSpec.links) {
        const linkGroup = robot.getObjectByName(`link:${link.name}`);
        if (!linkGroup) {
          continue;
        }

        linkGroup.traverse((obj) => {
          if (!(obj instanceof THREE.Mesh) || obj.userData.articraftVisual !== true) {
            return;
          }

          withMeshMaterials(obj, (material) => {
            restoreSegmentMaterial(material);
          });
        });
      }
    };
  }, [scene, renderOptions.showSegmentColors, urdfSpec]);

  useEffect(() => {
    disposeOverlayObjects(jointOverlayRef.current);
    jointOverlayRef.current = [];

    if (!renderOptions.showJointOverlay || !urdfSpec || !jointFrames || !scene) {
      return;
    }

    const robot = scene.getObjectByName('__articraft_robot__');
    if (!robot) {
      return;
    }

    const size = new THREE.Box3().setFromObject(robot).getSize(new THREE.Vector3());
    const extent = Math.max(size.x, size.y, size.z, 0.6);
    jointOverlayRef.current = attachJointOverlay(urdfSpec, jointFrames, extent);

    return () => {
      disposeOverlayObjects(jointOverlayRef.current);
      jointOverlayRef.current = [];
    };
  }, [jointFrames, renderOptions.showJointOverlay, scene, urdfSpec]);

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" />

      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-[#f3f3f3]/70">
          <p className="text-[11px] text-[#999]">{isStagingSelection ? "Buffering...." : "Loading…"}</p>
        </div>
      )}

      {isStagingBuffering && !loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-[#f3f3f3]/70">
          <p className="text-[11px] text-[#999]">Buffering....</p>
        </div>
      )}

      {error && !loading && !isStagingBuffering && (
        <div className="absolute inset-0 flex items-center justify-center bg-[#f3f3f3]/70">
          <div className="max-w-xs px-3 py-2 text-center">
            <p className="text-[11px] font-medium text-red-600">Failed to load model</p>
            <p className="mt-0.5 font-mono text-[10px] text-red-400">{error}</p>
          </div>
        </div>
      )}

      {!selectionKey && sceneReady && !loading && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <p className="text-[11px] text-[#bbb]">
            Select a record to view its 3D model
          </p>
        </div>
      )}
    </div>
  );
}
