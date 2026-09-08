import { useRef, useState, useEffect, Suspense } from 'react'
import ErrorBoundary from './ErrorBoundary.jsx'

import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'

export default function ModelViewer({ modelUrl, height = 400 }) {
  const containerRef = useRef(null)
  const rendererRef = useRef(null)
  const sceneRef = useRef(null)
  const cameraRef = useRef(null)
  const controlsRef = useRef(null)
  const frameRef = useRef(null)
  const [state, setState] = useState('loading')

  useEffect(() => {
    if (!modelUrl || !containerRef.current) return

    const container = containerRef.current
    let disposed = false

    // ── Setup ──
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x0a0a0a)
    sceneRef.current = scene

    const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 100)
    camera.position.set(0, 1.5, 3.5)
    cameraRef.current = camera

    let renderer
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false })
    } catch {
      if (!disposed) setState('error')
      return
    }
    renderer.setSize(container.clientWidth, container.clientHeight)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1
    container.appendChild(renderer.domElement)
    rendererRef.current = renderer

    // ── Lights ──
    scene.add(new THREE.AmbientLight(0xffffff, 0.5))
    const dirLight = new THREE.DirectionalLight(0xffffff, 1)
    dirLight.position.set(5, 5, 5)
    dirLight.castShadow = true
    scene.add(dirLight)
    const fillLight = new THREE.DirectionalLight(0xffffff, 0.3)
    fillLight.position.set(-3, 3, -3)
    scene.add(fillLight)

    // ── Controls ──
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.08
    controls.enablePan = false
    controls.minDistance = 2
    controls.maxDistance = 8
    controls.autoRotate = true
    controls.autoRotateSpeed = 2
    controls.target.set(0, 0.5, 0)
    controlsRef.current = controls

    // ── Ground shadow ──
    const groundGeo = new THREE.PlaneGeometry(10, 10)
    const groundMat = new THREE.ShadowMaterial({ opacity: 0.3 })
    const ground = new THREE.Mesh(groundGeo, groundMat)
    ground.rotation.x = -Math.PI / 2
    ground.position.y = -0.01
    ground.receiveShadow = true
    scene.add(ground)

    // ── Load model ──
    const loader = new GLTFLoader()
    loader.load(
      modelUrl,
      (gltf) => {
        if (disposed) return
        const model = gltf.scene

        // Centrar y escalar
        const box = new THREE.Box3().setFromObject(model)
        const size = box.getSize(new THREE.Vector3())
        const center = box.getCenter(new THREE.Vector3())
        const maxDim = Math.max(size.x, size.y, size.z)
        const scale = 2 / maxDim
        model.scale.setScalar(scale)
        model.position.sub(center.multiplyScalar(scale))
        model.position.y -= (box.min.y * scale)

        model.traverse((child) => {
          if (child.isMesh) {
            child.castShadow = true
            child.receiveShadow = true
          }
        })

        scene.add(model)
        setState('ready')
      },
      undefined,
      (err) => {
        console.error('Error loading 3D model:', err)
        if (!disposed) setState('error')
      }
    )

    // ── Render loop ──
    function animate() {
      if (disposed) return
      frameRef.current = requestAnimationFrame(animate)
      controls.update()
      renderer.render(scene, camera)
    }
    animate()

    // ── Resize ──
    function onResize() {
      if (!container || disposed) return
      const w = container.clientWidth
      const h = container.clientHeight
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
    }
    window.addEventListener('resize', onResize)

    // ── Cleanup ──
    return () => {
      disposed = true
      cancelAnimationFrame(frameRef.current)
      window.removeEventListener('resize', onResize)
      controls.dispose()
      renderer.dispose()
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement)
      }
    }
  }, [modelUrl])

  if (!modelUrl) return null

  return (
    <div style={{
      width: '100%',
      height,
      borderRadius: 12,
      overflow: 'hidden',
      border: '1px solid var(--line)',
      background: '#0a0a0a',
      position: 'relative',
    }}>
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />

      {/* Loading overlay */}
      {state === 'loading' && (
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'rgba(10,10,10,.8)',
        }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{
              width: 32, height: 32, margin: '0 auto 10px',
              border: '3px solid #272C34',
              borderTopColor: '#E8863E',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
            }} />
            <span style={{ fontSize: 12, color: '#8A9099' }}>Cargando modelo 3D...</span>
          </div>
        </div>
      )}

      {/* Error overlay */}
      {state === 'error' && (
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'var(--surface)',
          flexDirection: 'column', gap: 8,
        }}>
          <p style={{ fontSize: 13, color: 'var(--text-dim)', margin: 0 }}>
            No se pudo cargar el modelo 3D.
          </p>
          <p style={{ fontSize: 12, color: 'var(--text-dim)', margin: 0 }}>
            La imagen fue enviada. Nuestro equipo generará la referencia.
          </p>
        </div>
      )}

      {/* Badge */}
      {state === 'ready' && (
        <div style={{
          position: 'absolute', top: 12, left: 12,
          background: 'rgba(0,0,0,.7)',
          backdropFilter: 'blur(8px)',
          borderRadius: 8, padding: '6px 12px',
          fontSize: 11, color: '#E8863E',
          fontWeight: 600,
          fontFamily: 'var(--font-mono)',
          textTransform: 'uppercase',
          letterSpacing: '.05em',
          pointerEvents: 'none',
        }}>
          Vista 3D generada por IA
        </div>
      )}

      {/* Controls hint */}
      {state === 'ready' && (
        <div style={{
          position: 'absolute', bottom: 12, left: '50%',
          transform: 'translateX(-50%)',
          background: 'rgba(0,0,0,.6)',
          backdropFilter: 'blur(8px)',
          borderRadius: 6, padding: '4px 12px',
          fontSize: 11, color: '#8A9099',
          pointerEvents: 'none',
        }}>
          Arrastrá para rotar · Scroll para zoom
        </div>
      )}

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
