"use client";
import dynamic from "next/dynamic";
import {useState} from "react";
const Game=dynamic(()=>import("../components/Game"),{ssr:false});
export default function Home(){const[started,setStarted]=useState(false);if(!started)return <main className="menu"><div className="menuCard"><p className="eyebrow">LAGOS • 3D • STREET LIFE</p><h1>Lagos Street Hustler</h1><p>Start from the mainland, beat traffic, take missions and build a fictional Lagos fortune.</p><button onClick={()=>setStarted(true)}>PLAY NOW</button><div className="hint">WASD to move · Shift to sprint · E to interact</div></div></main>;return <Game/>}