import React, { useState, useRef, useEffect } from 'react';
import DeckGL from '@deck.gl/react';
import { ScatterplotLayer, PathLayer, ArcLayer, TextLayer, IconLayer } from '@deck.gl/layers';
import { FlyToInterpolator } from '@deck.gl/core';
import Map from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';
import { motion, AnimatePresence } from 'framer-motion';

const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';
const INITIAL_VIEW = { longitude: 65.0, latitude: 15.0, zoom: 4, pitch: 45, bearing: 0 };

const PORTS = [
  { name: 'Mundra SPM',      coordinates: [69.7, 22.8],  type: 'SPM Port',     color: [59,130,246] },
  { name: 'Vadinar SPM',     coordinates: [69.7, 22.4],  type: 'SPM Port',     color: [59,130,246] },
  { name: 'Paradip SPM',     coordinates: [86.6, 20.2],  type: 'SPM Port',     color: [59,130,246] },
  { name: 'Jamnagar (RIL)',  coordinates: [70.0, 22.4],  type: 'Refinery',     color: [239,68,68]  },
  { name: 'MRPL Mangaluru',  coordinates: [74.8, 12.9],  type: 'Refinery',     color: [239,68,68]  },
  { name: 'IOCL Paradip',    coordinates: [86.7, 20.3],  type: 'Refinery',     color: [239,68,68]  },
  { name: 'Visakhapatnam',   coordinates: [83.3, 17.7],  type: 'ISPRL Cavern', color: [16,185,129] },
  { name: 'Mangaluru Cavern',coordinates: [74.7, 12.8],  type: 'ISPRL Cavern', color: [16,185,129] },
  { name: 'Padur Cavern',    coordinates: [74.7, 13.2],  type: 'ISPRL Cavern', color: [16,185,129] },
];

const LNG_TERMINALS = [
  { name: 'Dahej LNG',       coordinates: [72.5, 21.7],  type: 'LNG Terminal', color: [168,85,247], cap: '17.5 MMTPA' },
  { name: 'Hazira LNG',      coordinates: [72.6, 21.1],  type: 'LNG Terminal', color: [168,85,247], cap: '5.0 MMTPA'  },
  { name: 'Kochi LNG',       coordinates: [76.2, 10.0],  type: 'LNG Terminal', color: [168,85,247], cap: '5.0 MMTPA'  },
  { name: 'Dabhol LNG',      coordinates: [73.1, 17.6],  type: 'LNG Terminal', color: [168,85,247], cap: '5.0 MMTPA'  },
  { name: 'Ennore LNG',      coordinates: [80.3, 13.2],  type: 'LNG Terminal', color: [168,85,247], cap: '5.0 MMTPA'  },
  { name: 'Mundra LNG',      coordinates: [69.7, 22.7],  type: 'LNG Terminal', color: [168,85,247], cap: '5.0 MMTPA'  },
];

const CHOKEPOINTS = [
  { name: 'Strait of Hormuz',  coordinates: [56.4, 26.5], risk: 0.85 },
  { name: 'Suez Canal',        coordinates: [32.5, 30.7], risk: 0.75 },
  { name: 'Bab-el-Mandeb',     coordinates: [43.4, 12.6], risk: 0.90 },
  { name: 'Strait of Malacca', coordinates: [103.8, 1.3], risk: 0.40 },
];

// Gas pipeline paths (approximate waypoints)
const GAS_PIPELINES = [
  { name: 'HVJ Pipeline',   path: [[72.5,21.7],[74.0,22.5],[76.5,23.5],[78.0,24.5],[79.5,25.5],[80.0,26.9]], color:[168,85,247,120] },
  { name: 'GREP Pipeline',  path: [[72.5,21.7],[71.0,22.0],[70.5,23.5],[70.2,25.0],[70.0,27.5]],            color:[168,85,247,100] },
];

// Crude pipeline paths
const CRUDE_PIPELINES = [
  { name: 'SMPL Pipeline',  path: [[69.7,22.4],[71.5,23.5],[74.0,24.8],[76.5,25.8],[78.5,26.5],[77.2,28.6]], color:[59,130,246,120] },
  { name: 'MDPL Pipeline',  path: [[69.7,22.8],[71.0,23.5],[74.0,25.0],[76.0,26.5],[77.2,28.6]],             color:[59,130,246,100] },
];

export default function Dashboard({ simulationData, vessels, onPortClick }) {
  const [viewState, setViewState] = useState({ ...INITIAL_VIEW, transitionDuration: 0 });
  const [tooltip, setTooltip] = useState(null);
  const [tick, setTick] = useState(0);
  const [vesselPositions, setVesselPositions] = useState(vessels || []);

  useEffect(() => { const i = setInterval(() => setTick(t => t + 1), 80); return () => clearInterval(i); }, []);

  // Animate vessel positions (drift them slowly)
  useEffect(() => {
    if (!vessels?.length) return;
    setVesselPositions(vessels.map(v => ({
      ...v,
      lon: v.lon + (Math.sin(tick * 0.002 + v.lon) * 0.002),
      lat: v.lat + (Math.cos(tick * 0.002 + v.lat) * 0.001),
    })));
  }, [tick, vessels]);

  // Fly to target on simulation
  useEffect(() => {
    const coords = simulationData?.crude?.scenario_parsed?.coordinates
                || simulationData?.gas?.scenario_parsed?.coordinates;
    if (coords) {
      setViewState(v => ({
        ...v, longitude: coords[0], latitude: coords[1] - 4,
        zoom: 5.5, pitch: 55, bearing: -10,
        transitionDuration: 2200,
        transitionInterpolator: new FlyToInterpolator({ speed: 1.2 }),
      }));
    }
  }, [simulationData]);

  const pulse = Math.abs(Math.sin(tick * 0.05));

  const commodity = simulationData?.commodity;
  const showGas   = commodity === 'gas' || commodity === 'both';
  const showCrude = commodity === 'crude' || commodity === 'both' || !commodity;

  const layers = [
    // ── Pipelines ──────────────────────────────────────────────────
    showCrude && new PathLayer({
      id: 'crude-pipelines', data: CRUDE_PIPELINES,
      getPath: d => d.path, getColor: d => d.color,
      getWidth: 2, widthMinPixels: 2, pickable: true,
      getDashArray: [4, 2], dashJustified: true,
    }),
    showGas && new PathLayer({
      id: 'gas-pipelines', data: GAS_PIPELINES,
      getPath: d => d.path, getColor: d => d.color,
      getWidth: 2, widthMinPixels: 2, pickable: true,
      getDashArray: [4, 2], dashJustified: true,
    }),

    // ── Chokepoint pulse rings ──────────────────────────────────────
    new ScatterplotLayer({
      id: 'chokepoint-ring', data: CHOKEPOINTS,
      getPosition: d => d.coordinates,
      getFillColor: [0,0,0,0], stroked: true, filled: false,
      getLineColor: d => [239,68,68,Math.round((1-pulse)*160)],
      getRadius: 65000 + pulse * 55000,
      lineWidthMinPixels: 1, radiusMinPixels: 14,
    }),
    new ScatterplotLayer({
      id: 'chokepoints', data: CHOKEPOINTS,
      getPosition: d => d.coordinates,
      getFillColor: d => [239,68,68, 140 + Math.round(pulse*100)],
      getRadius: 38000 + pulse*18000, radiusMinPixels: 8,
      pickable: true, autoHighlight: true,
    }),

    // ── SPM Ports ───────────────────────────────────────────────────
    showCrude && new ScatterplotLayer({
      id: 'ports', data: PORTS,
      getPosition: d => d.coordinates, getFillColor: d => [...d.color, 220],
      getRadius: 25000, radiusMinPixels: 6, radiusMaxPixels: 14,
      pickable: true, autoHighlight: true, highlightColor:[255,255,255,80],
    }),

    // ── LNG Terminals ───────────────────────────────────────────────
    showGas && new ScatterplotLayer({
      id: 'lng-terminals', data: LNG_TERMINALS,
      getPosition: d => d.coordinates, getFillColor: d => [...d.color, 210],
      getRadius: 28000, radiusMinPixels: 7, radiusMaxPixels: 16,
      pickable: true, autoHighlight: true, highlightColor:[255,255,255,80],
    }),

    // ── Labels ──────────────────────────────────────────────────────
    new TextLayer({
      id: 'port-labels',
      data: [...PORTS, ...(showGas ? LNG_TERMINALS : [])],
      getPosition: d => d.coordinates, getText: d => d.name,
      getSize: 11, getColor: [220,220,220,200], getPixelOffset: [0,-22], fontWeight: 600,
    }),
    new TextLayer({
      id: 'choke-labels', data: CHOKEPOINTS,
      getPosition: d => d.coordinates, getText: d => `⚠ ${d.name}`,
      getSize: 11, getColor: [239,100,100,230], getPixelOffset: [0,-26], fontWeight: 700,
    }),

    // ── Crude route arc ─────────────────────────────────────────────
    simulationData?.crude?.scenario_parsed?.source_coordinates && new ArcLayer({
      id: 'crude-arc',
      data:[{src: simulationData.crude.scenario_parsed.source_coordinates,
             tgt: simulationData.crude.scenario_parsed.coordinates}],
      getSourcePosition: d=>d.src, getTargetPosition: d=>d.tgt,
      getSourceColor:[251,191,36,200], getTargetColor:[59,130,246,200],
      getWidth:3, greatCircle:true,
    }),

    // ── Gas route arc ───────────────────────────────────────────────
    simulationData?.gas?.scenario_parsed?.source_coordinates && new ArcLayer({
      id: 'gas-arc',
      data:[{src: simulationData.gas.scenario_parsed.source_coordinates,
             tgt: simulationData.gas.scenario_parsed.coordinates}],
      getSourcePosition: d=>d.src, getTargetPosition: d=>d.tgt,
      getSourceColor:[168,85,247,200], getTargetColor:[34,211,238,200],
      getWidth:3, greatCircle:true,
    }),

    // ── Source dots ─────────────────────────────────────────────────
    simulationData?.crude?.scenario_parsed?.source_coordinates && new ScatterplotLayer({
      id:'crude-src', data:[{c:simulationData.crude.scenario_parsed.source_coordinates, n:'Ras Tanura (Crude)'}],
      getPosition:d=>d.c, getFillColor:[251,191,36,220], getRadius:35000, radiusMinPixels:8, pickable:true,
    }),
    simulationData?.gas?.scenario_parsed?.source_coordinates && new ScatterplotLayer({
      id:'gas-src', data:[{c:simulationData.gas.scenario_parsed.source_coordinates, n:'Ras Laffan (LNG)'}],
      getPosition:d=>d.c, getFillColor:[168,85,247,220], getRadius:32000, radiusMinPixels:7, pickable:true,
    }),

    // ── Animated Strategic Fleet Vessels ────────────────────────────
    vesselPositions.length > 0 && new ScatterplotLayer({
      id:'vessels',
      data: vesselPositions,
      getPosition: d => [d.lon, d.lat],
      getFillColor: d => {
        if (d.country === 'India') return [249, 115, 22, 230]; // Indian flag orange/saffron
        if (d.type?.includes('LNG')) return [34, 211, 238, 220]; // Cyan for LNG
        if (d.position_type === 'dead_reckoned') return [234, 179, 8, 200]; // Amber for Dead-reckoned
        return [250, 204, 21, 210]; // Gold/Yellow for crude tankers
      },
      getRadius: d => (d.country === 'India' ? 22000 : 18000),
      radiusMinPixels: 5, radiusMaxPixels: 12,
      pickable: true, autoHighlight: true,
    }),
    vesselPositions.length > 0 && new TextLayer({
      id:'vessel-labels', data: vesselPositions,
      getPosition: d => [d.lon, d.lat], 
      getText: d => `${d.flag || '🚢'} ${d.name}`,
      getSize: 10, getColor:[220,220,220,200], getPixelOffset:[0,-18], fontWeight:600,
    }),
  ].filter(Boolean);

  return (
    <div className="relative w-full h-full rounded-2xl overflow-hidden border border-white/10 shadow-2xl">
      <DeckGL
        viewState={viewState}
        onViewStateChange={({ viewState: vs }) => setViewState(vs)}
        controller={true} layers={layers}
        onHover={({ object, x, y }) => setTooltip(object ? { object, x, y } : null)}
        onClick={({ object }) => object && onPortClick?.(object)}
      >
        <Map mapStyle={MAP_STYLE} />
      </DeckGL>

      <div className="absolute inset-0 pointer-events-none shadow-[inset_0_0_120px_rgba(0,0,0,0.7)]" />

      {/* Top status bar */}
      <motion.div initial={{opacity:0,y:-20}} animate={{opacity:1,y:0}}
        className="absolute top-4 left-1/2 -translate-x-1/2 bg-black/60 backdrop-blur border border-white/10 rounded-full px-5 py-2 flex items-center gap-4 pointer-events-none">
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
        <span className="text-[10px] text-gray-300 uppercase tracking-widest">MARG Fleet Telemetry Active</span>
        <span className="w-px h-3 bg-white/15" />
        <span className="text-[10px] text-gray-500 font-mono">{new Date().toUTCString()}</span>
        {simulationData && <>
          <span className="w-px h-3 bg-white/15" />
          <span className="text-[10px] text-yellow-400 font-mono animate-pulse">⚠ CRISIS ACTIVE — {simulationData.region}</span>
        </>}
      </motion.div>

      {/* Chokepoint risk panel */}
      <motion.div initial={{opacity:0}} animate={{opacity:1}} transition={{delay:0.5}}
        className="absolute top-16 right-4 flex flex-col gap-1.5 pointer-events-none">
        {CHOKEPOINTS.map(cp => (
          <div key={cp.name} className="bg-black/65 backdrop-blur border border-red-500/25 rounded-lg px-3 py-1.5 flex items-center gap-3">
            <span className="text-[10px] text-gray-300 w-32 truncate">{cp.name}</span>
            <div className="w-16 h-1.5 bg-white/10 rounded-full overflow-hidden">
              <div className="h-full bg-red-500 rounded-full" style={{width:`${cp.risk*100}%`}} />
            </div>
            <span className="text-[10px] text-red-400 font-mono font-bold w-8">{Math.round(cp.risk*100)}%</span>
          </div>
        ))}
      </motion.div>

      {/* Legend */}
      <motion.div initial={{opacity:0,y:20}} animate={{opacity:1,y:0}} transition={{delay:0.7}}
        className="absolute bottom-5 right-4 bg-black/60 backdrop-blur border border-white/10 rounded-xl p-4 pointer-events-none flex flex-col gap-1.5">
        <p className="text-[9px] text-gray-500 uppercase tracking-widest mb-1 font-bold">Strategic Fleet Telemetry</p>
        {[
          {color:'bg-orange-500', label:'🇮🇳 Indian Sovereign Fleet'},
          {color:'bg-yellow-400', label:'🛢️ Crude Tanker / Charter'},
          {color:'bg-cyan-400',   label:'⚡ LNG / Gas Carrier'},
          {color:'bg-blue-500',   label:'SPM Port / Crude Pipeline'},
          {color:'bg-purple-500', label:'LNG Terminal / Gas Pipeline'},
          {color:'bg-emerald-500',label:'ISPRL Strategic Cavern'},
          {color:'bg-red-500',    label:'Refinery / Chokepoint'},
        ].map(l => (
          <div key={l.label} className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full ${l.color} flex-shrink-0`}/>
            <span className="text-[10px] text-gray-400">{l.label}</span>
          </div>
        ))}
        {(simulationData?.crude?.scenario_parsed?.distance_nm || simulationData?.gas?.scenario_parsed?.distance_nm) && (
          <div className="mt-1 pt-2 border-t border-white/10">
            {simulationData?.crude?.scenario_parsed?.distance_nm && (
              <p className="text-[10px] text-yellow-300">Crude: <span className="font-mono">{Math.round(simulationData.crude.scenario_parsed.distance_nm).toLocaleString()} nm</span></p>
            )}
            {simulationData?.gas?.scenario_parsed?.distance_nm && (
              <p className="text-[10px] text-purple-300">LNG: <span className="font-mono">{Math.round(simulationData.gas.scenario_parsed.distance_nm).toLocaleString()} nm</span></p>
            )}
          </div>
        )}
      </motion.div>

      {/* Hover tooltip */}
      <AnimatePresence>
        {tooltip && (
          <motion.div key="tt" initial={{opacity:0,scale:0.9}} animate={{opacity:1,scale:1}} exit={{opacity:0}}
            className="absolute pointer-events-none bg-black/90 backdrop-blur border border-white/20 rounded-xl px-3.5 py-2.5 text-xs z-50 shadow-2xl max-w-xs"
            style={{left:tooltip.x+14, top:tooltip.y-34}}>
            <div className="flex items-center gap-2">
              {tooltip.object.flag && <span className="text-base">{tooltip.object.flag}</span>}
              <p className="font-bold text-white text-[13px]">{tooltip.object.name}</p>
            </div>

            {tooltip.object.country && (
              <p className="text-gray-400 text-[10px] mt-0.5">
                {tooltip.object.country} · <span className="text-gray-500">{tooltip.object.category || 'Strategic Fleet'}</span>
              </p>
            )}

            {tooltip.object.type && (
              <div className="flex items-center gap-2 mt-1 text-[10px]">
                <span className="text-cyan-300 font-mono">{tooltip.object.type}</span>
                {tooltip.object.speed !== undefined && (
                  <span className="text-yellow-300 font-mono">· {tooltip.object.speed} kn</span>
                )}
                {tooltip.object.heading !== undefined && tooltip.object.heading > 0 && (
                  <span className="text-gray-400 font-mono">· {tooltip.object.heading}°</span>
                )}
              </div>
            )}

            {tooltip.object.position_type === 'dead_reckoned' && (
              <div className="mt-1.5 bg-yellow-500/15 border border-yellow-500/30 rounded px-1.5 py-0.5 text-[9px] text-yellow-300">
                ⚡ MARG Dead-Reckoned (+{tooltip.object.extrapolated_nm || 0} nm forward)
              </div>
            )}

            {tooltip.object.dark_zone && (
              <div className="mt-1 bg-red-500/20 border border-red-500/40 rounded px-1.5 py-0.5 text-[9px] text-red-300">
                ⚠ {tooltip.object.dark_zone}
              </div>
            )}

            {tooltip.object.cap && <p className="text-purple-300 mt-1 text-[10px]">{tooltip.object.cap}</p>}
            {tooltip.object.risk !== undefined && <p className="text-red-400 mt-1 text-[10px] font-bold">Risk: {Math.round(tooltip.object.risk*100)}%</p>}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
