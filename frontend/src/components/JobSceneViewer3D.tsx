import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three-stdlib';
import { API_BASE } from '../api';

interface RoomPreview {
  id: string;
  type?: string;
  polygon: number[][];
  height: number;
}

interface ScenePreviewResponse {
  job_id: string;
  rooms: RoomPreview[];
  bbox: number[];
}

const ROOM_COLORS: Record<string, number> = {
  Bedroom: 0x8e44ad,
  Kitchen: 0xe67e22,
  Bathroom: 0x3498db,
  'Living Room': 0x2ecc71,
  Balcony: 0x95a5a6,
  Corridor: 0x34495e,
  Dining: 0xe74c3c,
  Laundry: 0x1abc9c,
  default: 0x7f8c8d,
};

function getRoomColor(roomType?: string): number {
  if (!roomType) return ROOM_COLORS.default;
  return ROOM_COLORS[roomType] || ROOM_COLORS.default;
}

export default function JobSceneViewer3D({ jobId }: { jobId: string }) {
  const mountRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sceneData, setSceneData] = useState<ScenePreviewResponse | null>(null);

  // Fetch scene data (independent of mount ref)
  useEffect(() => {
    let mounted = true;
    
    fetch(`${API_BASE}/api/jobs/${jobId}/scene`)
      .then((res) => {
        if (!res.ok) {
          return res.json().then(err => {
            throw new Error(err.detail || 'Scene not found');
          });
        }
        return res.json();
      })
      .then((data: ScenePreviewResponse) => {
        if (mounted) {
          setSceneData(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (mounted) {
          setLoading(false);
          setError(err.message || 'Failed to load scene data');
        }
      });

    return () => {
      mounted = false;
    };
  }, [jobId]);

  // Render 3D scene once data is loaded and mount ref is available
  useEffect(() => {
    if (!mountRef.current || !sceneData) return;

    const mount = mountRef.current;
    const cleanup = renderScene(mount, sceneData);

    // Cleanup function
    return () => {
      if (cleanup) cleanup();
      mount.innerHTML = '';
    };
  }, [sceneData]);

  const renderScene = (mount: HTMLDivElement, data: ScenePreviewResponse) => {
    const { rooms, bbox } = data;

    // Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf0f0f0);

    // Camera setup
    const [minX, minY, maxX, maxY] = bbox;
    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    const rangeX = maxX - minX;
    const rangeY = maxY - minY;
    const maxRange = Math.max(rangeX, rangeY, 1);

    const camera = new THREE.PerspectiveCamera(
      50,
      mount.clientWidth / mount.clientHeight,
      0.1,
      1000
    );
    camera.position.set(centerX, maxRange * 0.8, centerY + maxRange * 0.8);
    camera.lookAt(centerX, 0, centerY);

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    mount.appendChild(renderer.domElement);

    // Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(centerX, 0, centerY);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;

    // Lighting
    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(5, 10, 7.5);
    scene.add(dirLight);

    // Build room geometries
    rooms.forEach((room) => {
      if (room.polygon.length < 3) return;

      // Create shape from polygon
      const shape = new THREE.Shape();
      room.polygon.forEach(([x, y], i) => {
        if (i === 0) {
          shape.moveTo(x, y);
        } else {
          shape.lineTo(x, y);
        }
      });

      // Extrude settings
      const extrudeSettings = {
        depth: room.height,
        bevelEnabled: false,
      };

      const geometry = new THREE.ExtrudeGeometry(shape, extrudeSettings);
      geometry.rotateX(-Math.PI / 2); // Rotate to stand upright

      const color = getRoomColor(room.type);
      const material = new THREE.MeshStandardMaterial({
        color,
        metalness: 0.1,
        roughness: 0.8,
      });

      const mesh = new THREE.Mesh(geometry, material);
      scene.add(mesh);

      // Add wireframe edges
      const edges = new THREE.EdgesGeometry(geometry);
      const line = new THREE.LineSegments(
        edges,
        new THREE.LineBasicMaterial({ color: 0x000000, linewidth: 1 })
      );
      mesh.add(line);
    });

    // Animation loop
    let animationFrameId: number;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // Handle window resize
    const handleResize = () => {
      if (!mount) return;
      camera.aspect = mount.clientWidth / mount.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(mount.clientWidth, mount.clientHeight);
    };
    window.addEventListener('resize', handleResize);

    // Cleanup function
    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
      
      // Dispose of all geometries and materials
      scene.traverse((object: THREE.Object3D) => {
        if (object instanceof THREE.Mesh) {
          object.geometry.dispose();
          if (object.material instanceof THREE.Material) {
            object.material.dispose();
          }
        } else if (object instanceof THREE.LineSegments) {
          object.geometry.dispose();
          if (object.material instanceof THREE.Material) {
            object.material.dispose();
          }
        }
      });
      
      renderer.dispose();
      controls.dispose();
      scene.clear();
    };
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96 bg-gray-50 rounded border">
        <p className="text-gray-600">Loading 3D preview...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-96 bg-gray-50 rounded border">
        <p className="text-red-600 font-medium mb-2">Unable to load 3D preview</p>
        <p className="text-gray-600 text-sm">{error}</p>
        <p className="text-gray-500 text-xs mt-4">The scene data may not have been generated yet or the job may have failed.</p>
      </div>
    );
  }

  return (
    <div className="w-full">
      <div
        ref={mountRef}
        className="w-full h-96 bg-white rounded border shadow-sm"
        style={{ minHeight: '400px' }}
      />
      <div className="mt-2 text-sm text-gray-500 flex flex-wrap gap-x-4 gap-y-1">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded" style={{ backgroundColor: '#8e44ad' }}></span>
          Bedroom
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded" style={{ backgroundColor: '#e67e22' }}></span>
          Kitchen
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded" style={{ backgroundColor: '#3498db' }}></span>
          Bathroom
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded" style={{ backgroundColor: '#2ecc71' }}></span>
          Living Room
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded" style={{ backgroundColor: '#34495e' }}></span>
          Corridor
        </span>
      </div>
    </div>
  );
}
