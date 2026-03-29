import { useEffect, useRef } from 'react'
import * as THREE from 'three'

interface TrackPoint { x: number; y: number; z: number }
interface Props {
  primaryTrack: TrackPoint[]
  secondaryTrack: TrackPoint[]
  primaryName: string
  secondaryName: string
  tcaPoint?: TrackPoint
}

const EARTH_RADIUS = 6371
const SCALE = 1 / 1000  // km → scene units

export default function OrbitViewer({ primaryTrack, secondaryTrack, primaryName, secondaryName, tcaPoint }: Props) {
  const mountRef = useRef<HTMLDivElement>(null)
  const rendererRef = useRef<THREE.WebGLRenderer>()
  const frameRef = useRef<number>()

  useEffect(() => {
    if (!mountRef.current) return
    const el = mountRef.current
    const W = el.clientWidth
    const H = el.clientHeight

    // Scene
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(45, W / H, 0.001, 100)
    camera.position.set(0, 8, 14)
    camera.lookAt(0, 0, 0)

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(W, H)
    renderer.setPixelRatio(window.devicePixelRatio)
    renderer.setClearColor(0x000000, 0)
    el.appendChild(renderer.domElement)
    rendererRef.current = renderer

    // Stars
    const starGeo = new THREE.BufferGeometry()
    const starPositions: number[] = []
    for (let i = 0; i < 2000; i++) {
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      const r = 40 + Math.random() * 10
      starPositions.push(
        r * Math.sin(phi) * Math.cos(theta),
        r * Math.sin(phi) * Math.sin(theta),
        r * Math.cos(phi),
      )
    }
    starGeo.setAttribute('position', new THREE.Float32BufferAttribute(starPositions, 3))
    scene.add(new THREE.Points(starGeo, new THREE.PointsMaterial({ color: 0xffffff, size: 0.05, opacity: 0.7, transparent: true })))

    // Earth sphere
    const earthGeo = new THREE.SphereGeometry(EARTH_RADIUS * SCALE, 48, 48)
    const earthMat = new THREE.MeshPhongMaterial({
      color: 0x1a3a5c,
      emissive: 0x061020,
      specular: 0x4488cc,
      shininess: 30,
    })
    const earth = new THREE.Mesh(earthGeo, earthMat)
    scene.add(earth)

    // Atmosphere glow
    const atmGeo = new THREE.SphereGeometry(EARTH_RADIUS * SCALE * 1.03, 32, 32)
    const atmMat = new THREE.MeshPhongMaterial({
      color: 0x2266aa,
      transparent: true,
      opacity: 0.12,
      side: THREE.FrontSide,
    })
    scene.add(new THREE.Mesh(atmGeo, atmMat))

    // Grid lines on Earth surface
    const gridMat = new THREE.LineBasicMaterial({ color: 0x1a4060, transparent: true, opacity: 0.4 })
    for (let lat = -75; lat <= 75; lat += 25) {
      const pts: THREE.Vector3[] = []
      for (let lon = 0; lon <= 360; lon += 5) {
        const r = EARTH_RADIUS * SCALE * 1.001
        const phi = (lat * Math.PI) / 180
        const theta = (lon * Math.PI) / 180
        pts.push(new THREE.Vector3(r * Math.cos(phi) * Math.cos(theta), r * Math.sin(phi), r * Math.cos(phi) * Math.sin(theta)))
      }
      scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), gridMat))
    }

    // Lighting
    scene.add(new THREE.AmbientLight(0x223355, 2))
    const sun = new THREE.DirectionalLight(0xffffff, 1.5)
    sun.position.set(20, 10, 10)
    scene.add(sun)

    // Helper: build orbit line from track points
    function buildOrbitLine(track: TrackPoint[], color: number, opacity = 1.0) {
      if (!track || track.length < 2) return null
      const pts = track.map(p => new THREE.Vector3(p.x * SCALE, p.y * SCALE, p.z * SCALE))
      const geo = new THREE.BufferGeometry().setFromPoints(pts)
      const mat = new THREE.LineBasicMaterial({ color, transparent: opacity < 1, opacity })
      return new THREE.Line(geo, mat)
    }

    // Helper: animated satellite dot
    function buildSatDot(color: number, size = 0.05) {
      const geo = new THREE.SphereGeometry(size, 8, 8)
      const mat = new THREE.MeshBasicMaterial({ color })
      return new THREE.Mesh(geo, mat)
    }

    // Primary track — blue
    const primaryLine = buildOrbitLine(primaryTrack, 0x3b82f6, 0.8)
    if (primaryLine) scene.add(primaryLine)

    // Secondary track — amber
    const secondaryLine = buildOrbitLine(secondaryTrack, 0xf59e0b, 0.8)
    if (secondaryLine) scene.add(secondaryLine)

    // Satellite dots
    const priDot = buildSatDot(0x60a5fa, 0.07)
    const secDot = buildSatDot(0xfbbf24, 0.07)
    scene.add(priDot)
    scene.add(secDot)

    // Initial dot positions
    if (primaryTrack.length > 0) {
      const p = primaryTrack[0]
      priDot.position.set(p.x * SCALE, p.y * SCALE, p.z * SCALE)
    }
    if (secondaryTrack.length > 0) {
      const p = secondaryTrack[0]
      secDot.position.set(p.x * SCALE, p.y * SCALE, p.z * SCALE)
    }

    // TCA closest approach marker
    if (tcaPoint) {
      const markerGeo = new THREE.SphereGeometry(0.1, 12, 12)
      const markerMat = new THREE.MeshBasicMaterial({ color: 0xef4444, transparent: true, opacity: 0.9 })
      const marker = new THREE.Mesh(markerGeo, markerMat)
      marker.position.set(tcaPoint.x * SCALE, tcaPoint.y * SCALE, tcaPoint.z * SCALE)
      scene.add(marker)

      // Pulsing ring around TCA
      const ringGeo = new THREE.RingGeometry(0.12, 0.16, 24)
      const ringMat = new THREE.MeshBasicMaterial({ color: 0xef4444, transparent: true, opacity: 0.6, side: THREE.DoubleSide })
      const ring = new THREE.Mesh(ringGeo, ringMat)
      ring.position.copy(marker.position)
      ring.lookAt(camera.position)
      scene.add(ring)
    }

    // Mouse drag rotation
    let isDragging = false
    let lastMouse = { x: 0, y: 0 }
    let rotY = 0, rotX = 0
    const pivot = new THREE.Group()
    scene.add(pivot)

    const onMouseDown = (e: MouseEvent) => { isDragging = true; lastMouse = { x: e.clientX, y: e.clientY } }
    const onMouseUp = () => { isDragging = false }
    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging) return
      rotY += (e.clientX - lastMouse.x) * 0.005
      rotX += (e.clientY - lastMouse.y) * 0.005
      rotX = Math.max(-Math.PI / 3, Math.min(Math.PI / 3, rotX))
      lastMouse = { x: e.clientX, y: e.clientY }
    }
    const onWheel = (e: WheelEvent) => {
      camera.position.multiplyScalar(1 + e.deltaY * 0.001)
    }

    renderer.domElement.addEventListener('mousedown', onMouseDown)
    window.addEventListener('mouseup', onMouseUp)
    window.addEventListener('mousemove', onMouseMove)
    renderer.domElement.addEventListener('wheel', onWheel)

    // Animation
    let frame = 0
    let priIdx = 0, secIdx = 0
    const SAT_SPEED = 3 // steps per frame

    const animate = () => {
      frameRef.current = requestAnimationFrame(animate)
      frame++

      // Auto-rotate when not dragging
      if (!isDragging) rotY += 0.002

      earth.rotation.y = rotY
      camera.position.x = 14 * Math.sin(rotY * 0.3) * Math.cos(rotX * 0.5)
      camera.position.z = 14 * Math.cos(rotY * 0.3) * Math.cos(rotX * 0.5)
      camera.position.y = 8 + 6 * Math.sin(rotX * 0.5)
      camera.lookAt(0, 0, 0)

      // Animate satellite dots along tracks
      if (frame % SAT_SPEED === 0) {
        if (primaryTrack.length > 0) {
          priIdx = (priIdx + 1) % primaryTrack.length
          const p = primaryTrack[priIdx]
          priDot.position.set(p.x * SCALE, p.y * SCALE, p.z * SCALE)
        }
        if (secondaryTrack.length > 0) {
          secIdx = (secIdx + 1) % secondaryTrack.length
          const p = secondaryTrack[secIdx]
          secDot.position.set(p.x * SCALE, p.y * SCALE, p.z * SCALE)
        }
      }

      renderer.render(scene, camera)
    }
    animate()

    // Handle resize
    const onResize = () => {
      const w = el.clientWidth, h = el.clientHeight
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
    }
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(frameRef.current!)
      renderer.domElement.removeEventListener('mousedown', onMouseDown)
      window.removeEventListener('mouseup', onMouseUp)
      window.removeEventListener('mousemove', onMouseMove)
      renderer.domElement.removeEventListener('wheel', onWheel)
      window.removeEventListener('resize', onResize)
      renderer.dispose()
      if (el.contains(renderer.domElement)) el.removeChild(renderer.domElement)
    }
  }, [primaryTrack, secondaryTrack, tcaPoint])

  return (
    <div className="relative w-full h-full">
      <div ref={mountRef} className="w-full h-full" />
      {/* Legend */}
      <div className="absolute bottom-3 left-3 flex flex-col gap-1">
        <div className="flex items-center gap-2 bg-black/60 rounded px-2 py-1">
          <div className="w-3 h-1 rounded" style={{ background: '#3b82f6' }} />
          <span className="text-xs font-mono text-blue-300 max-w-[140px] truncate">{primaryName}</span>
        </div>
        <div className="flex items-center gap-2 bg-black/60 rounded px-2 py-1">
          <div className="w-3 h-1 rounded" style={{ background: '#f59e0b' }} />
          <span className="text-xs font-mono text-amber-300 max-w-[140px] truncate">{secondaryName}</span>
        </div>
        {tcaPoint && (
          <div className="flex items-center gap-2 bg-black/60 rounded px-2 py-1">
            <div className="w-3 h-3 rounded-full" style={{ background: '#ef4444' }} />
            <span className="text-xs font-mono text-red-300">TCA Point</span>
          </div>
        )}
      </div>
      <div className="absolute top-3 right-3 text-xs text-slate-600 font-mono">drag to rotate · scroll to zoom</div>
    </div>
  )
}
