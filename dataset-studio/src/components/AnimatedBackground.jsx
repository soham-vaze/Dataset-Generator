import { useEffect, useRef, useMemo } from "react";

export default function AnimatedBackground({ variant = "default" }) {
  const canvasRef = useRef(null);
  const mouseRef = useRef({ x: -1000, y: -1000 });

  const config = useMemo(() => {
    if (variant === "login") {
      return { count: 70, connectionDist: 140, mouseRadius: 180, baseOpacity: 0.7 };
    }
    return { count: 40, connectionDist: 110, mouseRadius: 150, baseOpacity: 0.5 };
  }, [variant]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let animationId;
    let particles = [];
    let time = 0;

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = window.innerWidth * dpr;
      canvas.height = window.innerHeight * dpr;
      canvas.style.width = window.innerWidth + "px";
      canvas.style.height = window.innerHeight + "px";
      ctx.scale(dpr, dpr);
    };
    resize();
    window.addEventListener("resize", resize);

    const handleMouseMove = (e) => {
      mouseRef.current = { x: e.clientX, y: e.clientY };
    };
    window.addEventListener("mousemove", handleMouseMove);

    // Particle system with varied behaviors
    const hueRanges = [
      [260, 290], // purple
      [220, 250], // blue
      [180, 210], // cyan
      [280, 310], // violet-pink
    ];

    for (let i = 0; i < config.count; i++) {
      const rangeIndex = Math.floor(Math.random() * hueRanges.length);
      const [hueMin, hueMax] = hueRanges[rangeIndex];
      particles.push({
        x: Math.random() * window.innerWidth,
        y: Math.random() * window.innerHeight,
        size: Math.random() * 1.8 + 0.4,
        baseSpeedX: (Math.random() - 0.5) * 0.2,
        baseSpeedY: (Math.random() - 0.5) * 0.2,
        opacity: Math.random() * 0.35 + 0.08,
        hue: Math.random() * (hueMax - hueMin) + hueMin,
        saturation: 55 + Math.random() * 25,
        lightness: 55 + Math.random() * 20,
        phase: Math.random() * Math.PI * 2,
        driftAmp: Math.random() * 0.3 + 0.1,
        pulseSpeed: 0.01 + Math.random() * 0.02,
      });
    }

    const w = () => window.innerWidth;
    const h = () => window.innerHeight;

    const animate = () => {
      time += 0.008;
      ctx.clearRect(0, 0, w(), h());

      const mouse = mouseRef.current;

      particles.forEach((p) => {
        // Organic drift
        const driftX = Math.sin(time * 0.7 + p.phase) * p.driftAmp;
        const driftY = Math.cos(time * 0.5 + p.phase * 1.3) * p.driftAmp;

        p.x += p.baseSpeedX + driftX * 0.15;
        p.y += p.baseSpeedY + driftY * 0.15;

        // Mouse interaction - gentle push
        const dx = p.x - mouse.x;
        const dy = p.y - mouse.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < config.mouseRadius && dist > 0) {
          const force = (1 - dist / config.mouseRadius) * 0.4;
          p.x += (dx / dist) * force;
          p.y += (dy / dist) * force;
        }

        // Wrap
        if (p.x < -20) p.x = w() + 20;
        if (p.x > w() + 20) p.x = -20;
        if (p.y < -20) p.y = h() + 20;
        if (p.y > h() + 20) p.y = -20;

        // Pulsing opacity
        const pulseOpacity = p.opacity * (0.7 + 0.3 * Math.sin(time * p.pulseSpeed * 60 + p.phase));

        // Draw glow
        const gradient = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.size * 4);
        gradient.addColorStop(0, `hsla(${p.hue}, ${p.saturation}%, ${p.lightness}%, ${pulseOpacity})`);
        gradient.addColorStop(0.4, `hsla(${p.hue}, ${p.saturation}%, ${p.lightness}%, ${pulseOpacity * 0.4})`);
        gradient.addColorStop(1, `hsla(${p.hue}, ${p.saturation}%, ${p.lightness}%, 0)`);

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * 4, 0, Math.PI * 2);
        ctx.fillStyle = gradient;
        ctx.fill();

        // Draw core
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `hsla(${p.hue}, ${p.saturation}%, ${p.lightness + 15}%, ${pulseOpacity * 1.5})`;
        ctx.fill();
      });

      // Neural network connections
      for (let i = 0; i < particles.length; i++) {
        const a = particles[i];
        for (let j = i + 1; j < particles.length; j++) {
          const b = particles[j];
          const dist = Math.hypot(a.x - b.x, a.y - b.y);
          if (dist < config.connectionDist) {
            const alpha = 0.04 * (1 - dist / config.connectionDist);

            // Mouse proximity boost
            const midX = (a.x + b.x) / 2;
            const midY = (a.y + b.y) / 2;
            const mouseDist = Math.hypot(midX - mouse.x, midY - mouse.y);
            const mouseBoost = mouseDist < config.mouseRadius * 1.5
              ? 1 + (1 - mouseDist / (config.mouseRadius * 1.5)) * 2
              : 1;

            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.strokeStyle = `rgba(139, 92, 246, ${alpha * mouseBoost})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }

      animationId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener("resize", resize);
      window.removeEventListener("mousemove", handleMouseMove);
    };
  }, [variant, config]);

  return (
    <>
      <div className="aurora-bg" />
      <canvas
        ref={canvasRef}
        className="fixed inset-0 z-0 pointer-events-none"
        style={{ opacity: config.baseOpacity }}
      />
    </>
  );
}
