import { memo } from 'react'
import { ShaderGradient, ShaderGradientCanvas } from '@shadergradient/react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'

// The page's one WebGL effect (DESIGN.md: hero only). Colours are the ink, brand
// and signal values. Loaded lazily from App; the hero's CSS gradient shows until it
// paints or if WebGL is unavailable.
// - memo: App re-renders on every 1s poll during a run and this must not.
// - lazyLoad={false}: the library's default unmounts the canvas whenever the hero
//   leaves the viewport, so scrolling back up rebuilt the WebGL context and restarted
//   the animation from frame one (the visible "reload"). It now mounts once.
// - grain off: the noise pass cost GPU on every frame for little visible gain.
// - its own AnimatePresence: App's backdrop uses initial={false}, which motion passes
//   down to every motion child, so without this the canvas popped in at full opacity.
// - enableTransition off: the library otherwise flies the camera from its default
//   pose to ours on the first frames, a visible swoop with black gaps on every load.
export default memo(function HeroGradient() {
  const reduce = useReducedMotion()
  return (
    <AnimatePresence>
      <motion.div key="gradient" className="absolute inset-0" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 1.2, ease: 'easeOut' }}>
        <ShaderGradientCanvas style={{ position: 'absolute', inset: 0 }} pixelDensity={1} fov={45} pointerEvents="none" lazyLoad={false}>
          <ShaderGradient
            control="props" type="plane" animate={reduce ? 'off' : 'on'}
            uSpeed={0.12} uStrength={2.4} uDensity={1.3} uFrequency={5.5} uAmplitude={1}
            positionX={-1.4} positionY={0} positionZ={0} rotationX={0} rotationY={10} rotationZ={50}
            color1="#0a1530" color2="#2563eb" color3="#38bdf8" reflection={0.1}
            cAzimuthAngle={180} cPolarAngle={90} cDistance={3.6} cameraZoom={1}
            lightType="3d" brightness={1.1} grain="off" enableTransition={false}
          />
        </ShaderGradientCanvas>
      </motion.div>
    </AnimatePresence>
  )
})
