"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { Environment, PerspectiveCamera, Text } from "@react-three/drei";
import { Physics, RigidBody } from "@react-three/rapier";
import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";

type Mission = {
  id: string;
  title: string;
  reward: string;
  xp: number;
  description: string;
  target: [number, number];
};

const missions: Mission[] = [
  { id: "first-day", title: "First Day in Lagos", reward: "2500", xp: 100, description: "Meet your first street contact.", target: [0, 28] },
  { id: "food-run", title: "Food Delivery", reward: "15000", xp: 250, description: "Reach the market before traffic wins.", target: [-18, -5] },
  { id: "industrial", title: "Industrial Delivery", reward: "2500000", xp: 1200, description: "Drive to the fictional refinery district.", target: [28, -55] },
];

const locations = [
  { name: "Yaba Market", x: 0, z: 30 },
  { name: "Lagos Island", x: -38, z: 5 },
  { name: "Victoria Island", x: 38, z: 5 },
  { name: "Lekki", x: 42, z: -35 },
  { name: "Industrial Zone", x: 28, z: -55 },
];

function Building({ x, z, h = 8, w = 5, d = 5 }: { x: number; z: number; h?: number; w?: number; d?: number }) {
  return (
    <group position={[x, h / 2, z]}>
      <mesh castShadow>
        <boxGeometry args={[w, h, d]} />
        <meshStandardMaterial color="#68736f" />
      </mesh>
    </group>
  );
}

function Landmark({ name, position, color }: { name: string; position: [number, number, number]; color: string }) {
  return (
    <group position={position}>
      <mesh castShadow>
        <cylinderGeometry args={[2.5, 2.5, 6, 20]} />
        <meshStandardMaterial color={color} metalness={0.35} roughness={0.55} />
      </mesh>
      <Text position={[0, 5, 0]} fontSize={1.4} color="#ffffff" anchorX="center">
        {name}
      </Text>
    </group>
  );
}

function Refinery() {
  return (
    <group position={[28, 0, -55]}>
      <Text position={[0, 12, 0]} fontSize={2.1} color="#f2c94c" anchorX="center">
        FICTIONAL REFINERY ZONE
      </Text>
      <mesh position={[0, 5, 0]} castShadow>
        <cylinderGeometry args={[5, 5, 10, 24]} />
        <meshStandardMaterial color="#8b9690" metalness={0.5} roughness={0.4} />
      </mesh>
      <mesh position={[8, 3, -3]} castShadow>
        <cylinderGeometry args={[2, 2, 6, 20]} />
        <meshStandardMaterial color="#a7aaa2" metalness={0.45} roughness={0.4} />
      </mesh>
      {[
        [-7, 2, 0],
        [7, 2, 5],
        [0, 2, 8],
      ].map((p, i) => (
        <mesh key={i} position={p as [number, number, number]} rotation={[0, 0, Math.PI / 2]} castShadow>
          <cylinderGeometry args={[0.45, 0.45, 14, 12]} />
          <meshStandardMaterial color="#c0a84a" metalness={0.4} />
        </mesh>
      ))}
    </group>
  );
}

function World({ night }: { night: boolean }) {
  const blocks = useMemo(
    () =>
      Array.from({ length: 46 }, (_, i) => ({
        x: (i % 2 ? -1 : 1) * (10 + (i % 7) * 6),
        z: -70 + Math.floor(i / 2) * 6.5,
        h: 5 + (i % 7) * 2,
      })),
    [],
  );

  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[180, 180]} />
        <meshStandardMaterial color={night ? "#17201d" : "#66736c"} />
      </mesh>
      <mesh position={[0, 0.02, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[10, 150]} />
        <meshStandardMaterial color="#202525" />
      </mesh>
      <mesh position={[0, 0.03, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[150, 10]} />
        <meshStandardMaterial color="#202525" />
      </mesh>
      {blocks.map((b, i) => <Building key={i} {...b} />)}
      <Landmark name="YABA" position={[0, 2.8, 30]} color="#d39a3d" />
      <Landmark name="VI" position={[38, 2.8, 5]} color="#6389b6" />
      <Landmark name="LEKKI" position={[42, 2.8, -35]} color="#5c9a76" />
      <Refinery />
      <Text position={[0, 0.2, 48]} rotation={[-Math.PI / 2, 0, 0]} fontSize={1.5} color="#e9dfbf">
        YABA MARKET DISTRICT
      </Text>
    </group>
  );
}

function Player({ onMove }: { onMove: (x: number, z: number) => void }) {
  const ref = useRef<any>(null);
  const keys = useRef<Record<string, boolean>>({});

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (["INPUT", "TEXTAREA", "BUTTON"].includes((e.target as HTMLElement)?.tagName)) return;
      keys.current[e.key.toLowerCase()] = true;
    };
    const up = (e: KeyboardEvent) => { keys.current[e.key.toLowerCase()] = false; };
    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    return () => {
      window.removeEventListener("keydown", down);
      window.removeEventListener("keyup", up);
    };
  }, []);

  useFrame((_, delta) => {
    if (!ref.current) return;
    const k = keys.current;
    const x = (k.d || k.arrowright ? 1 : 0) - (k.a || k.arrowleft ? 1 : 0);
    const z = (k.s || k.arrowdown ? 1 : 0) - (k.w || k.arrowup ? 1 : 0);
    const v = new THREE.Vector3(x, 0, z);

    if (v.lengthSq()) {
      v.normalize().multiplyScalar((k.shift ? 12 : 6) * Math.min(delta, 0.05));
      const p = ref.current.translation();
      const nx = THREE.MathUtils.clamp(p.x + v.x, -82, 82);
      const nz = THREE.MathUtils.clamp(p.z + v.z, -82, 82);
      ref.current.setNextKinematicTranslation({ x: nx, y: p.y, z: nz });
      onMove(nx, nz);
    }
  });

  return (
    <RigidBody ref={ref} type="kinematicPosition" position={[0, 1, 12]} colliders="cuboid">
      <mesh castShadow>
        <capsuleGeometry args={[0.65, 0.9, 8, 16]} />
        <meshStandardMaterial color="#f2c94c" />
      </mesh>
    </RigidBody>
  );
}

function Traffic() {
  const cars = useMemo(
    () => Array.from({ length: 12 }, (_, i) => ({ x: i % 2 ? 2.2 : -2.2, z: -68 + i * 12 })),
    [],
  );
  return (
    <>
      {cars.map((c, i) => (
        <RigidBody key={i} type="fixed" position={[c.x, 0.6, c.z]}>
          <mesh castShadow>
            <boxGeometry args={[1.7, 0.9, 3.4]} />
            <meshStandardMaterial color={i % 3 === 0 ? "#d95d39" : "#d8d8d2"} />
          </mesh>
        </RigidBody>
      ))}
    </>
  );
}

function Scene({ onMove, night }: { onMove: (x: number, z: number) => void; night: boolean }) {
  return (
    <Canvas shadows camera={{ position: [0, 8, 18], fov: 65 }}>
      <PerspectiveCamera makeDefault position={[0, 8, 18]} fov={65} />
      <color attach="background" args={[night ? "#07121c" : "#8eb4c0"]} />
      <ambientLight intensity={night ? 0.22 : 0.75} />
      <directionalLight position={[20, 30, 10]} intensity={night ? 0.35 : 3} castShadow />
      <Environment preset="city" />
      <Physics gravity={[0, -9.81, 0]}>
        <World night={night} />
        <Traffic />
        <Player onMove={onMove} />
      </Physics>
    </Canvas>
  );
}

function formatMoney(value: string) {
  const n = BigInt(value);
  const units: [bigint, string][] = [
    [1000000000000000000000000n, "Qa"],
    [1000000000000000000000n, "Z"],
    [1000000000000000000n, "Qi"],
    [1000000000000000n, "Qa"],
    [1000000000000n, "T"],
    [1000000000n, "B"],
    [1000000n, "M"],
    [1000n, "K"],
  ];
  for (const [unit, suffix] of units) {
    if (n >= unit) return "₦" + (n / unit).toString() + suffix;
  }
  return "₦" + n.toString();
}

export default function Game() {
  const [money, setMoney] = useState("2500000");
  const [xp, setXp] = useState(0);
  const [active, setActive] = useState(missions[0]);
  const [position, setPosition] = useState({ x: 0, z: 12 });
  const [mapOpen, setMapOpen] = useState(true);
  const [message, setMessage] = useState("Explore Lagos. Reach the highlighted mission area.");
  const [hour, setHour] = useState(8);

  useEffect(() => {
    const id = window.setInterval(() => setHour((h) => (h + 0.05) % 24), 1000);
    return () => window.clearInterval(id);
  }, []);

  const night = hour > 18 || hour < 6;

  const distance = Math.hypot(position.x - active.target[0], position.z - active.target[1]);
  const canComplete = distance < 7;

  useEffect(() => {
    if (canComplete) setMessage("MISSION READY — press E or tap Complete.");
  }, [canComplete]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === "m") setMapOpen((v) => !v);
      if (e.key.toLowerCase() === "e" && canComplete) {
        setMoney((v) => (BigInt(v) + BigInt(active.reward)).toString());
        setXp((v) => v + active.xp);
        setMessage("Mission completed! Choose your next hustle.");
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active, canComplete]);

  const selectMission = (mission: Mission) => {
    setActive(mission);
    setMessage("New mission selected. Follow the marker on the map.");
  };

  const mapPoint = (x: number, z: number) => ({
    left: `${50 + (x / 90) * 46}%`,
    top: `${50 + (z / 90) * 46}%`,
  });

  return (
    <div className="gameRoot">
      <Scene onMove={(x, z) => setPosition({ x, z })} night={night} />

      <div className="hud">
        <div className="panel stats">
          <div><span>Cash</span><strong>{formatMoney(money)}</strong></div>
          <div><span>XP</span><strong>{xp}</strong></div>
          <div><span>Level</span><strong>{Math.floor(xp / 500) + 1}</strong></div>
          <div><span>Time</span><strong>{String(Math.floor(hour)).padStart(2, "0")}:00</strong></div>
        </div>

        <div className="panel mission">
          <div className="label">ACTIVE HUSTLE</div>
          <strong>{active.title}</strong>
          <p>{active.description}</p>
          <div className="hint">{message}</div>
          <button
            disabled={!canComplete}
            onClick={() => {
              if (!canComplete) return;
              setMoney((v) => (BigInt(v) + BigInt(active.reward)).toString());
              setXp((v) => v + active.xp);
              setMessage("Mission completed! Choose your next hustle.");
            }}
          >
            {canComplete ? `Complete +₦${active.reward}` : `Go to target · ${Math.ceil(distance)}m`}
          </button>
        </div>
      </div>

      <div className="mapPanel">
        <div className="mapHeader">
          <strong>LAGOS MAP</strong>
          <button onClick={() => setMapOpen((v) => !v)}>{mapOpen ? "×" : "MAP"}</button>
        </div>
        {mapOpen && (
          <div className="map">
            <div className="road roadH" />
            <div className="road roadV" />
            {locations.map((location) => {
              const p = mapPoint(location.x, location.z);
              return (
                <button
                  key={location.name}
                  className="mapLocation"
                  style={p}
                  title={location.name}
                  onClick={() => setMessage(`Location selected: ${location.name}`)}
                >
                  ●
                </button>
              );
            })}
            <div className="playerDot" style={mapPoint(position.x, position.z)} />
            <div className="targetDot" style={mapPoint(active.target[0], active.target[1])} />
          </div>
        )}
        <div className="mapLegend">● You · ◆ Mission · W A S D Move · Shift Sprint · E Interact · M Map</div>
      </div>

      <div className="missionBar">
        {missions.map((mission, index) => (
          <button key={mission.id} className={mission.id === active.id ? "active" : ""} onClick={() => selectMission(mission)}>
            {index + 1}. {mission.title}
          </button>
        ))}
      </div>
    </div>
  );
}
