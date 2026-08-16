'use client';
import { useEffect, useRef } from 'react';

// Animated 3D perspective grid canvas with glowing laser scan-lines.
// GPU-accelerated via will-change & requestAnimationFrame.
// Completely isolated — never triggers parent re-renders.
export default function GridBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let raf: number;
    let scanY = 0;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    const COLS = 28;
    const ROWS = 18;

    const draw = (t: number) => {
      const W = canvas.width;
      const H = canvas.height;
      ctx.clearRect(0, 0, W, H);

      // Perspective vanishing point
      const vx = W / 2;
      const vy = H * 0.38;
      const horizon = vy;

      // Vertical lines
      for (let i = 0; i <= COLS; i++) {
        const rx = (i / COLS) * W;
        const alpha = 0.06 + 0.04 * Math.sin(t * 0.0008 + i * 0.4);
        ctx.strokeStyle = `rgba(16,185,129,${alpha})`;
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        ctx.moveTo(vx + (rx - vx) * 0.05, horizon);
        ctx.lineTo(rx, H);
        ctx.stroke();
      }

      // Horizontal lines — perspective foreshortened
      for (let j = 0; j <= ROWS; j++) {
        const t2 = Math.pow(j / ROWS, 1.6);
        const y = horizon + t2 * (H - horizon);
        const xl = vx - (vx) * t2;
        const xr = vx + (W - vx) * t2;
        const alpha = 0.04 + 0.04 * t2 * Math.sin(t * 0.0006 + j * 0.3);
        ctx.strokeStyle = `rgba(16,185,129,${alpha})`;
        ctx.lineWidth = 0.4;
        ctx.beginPath();
        ctx.moveTo(xl, y);
        ctx.lineTo(xr, y);
        ctx.stroke();
      }

      // Glowing intersection dots (slow pulse)
      for (let i = 1; i < COLS; i += 4) {
        for (let j = 1; j < ROWS; j += 4) {
          const t2 = Math.pow(j / ROWS, 1.6);
          const y = horizon + t2 * (H - horizon);
          const rx = (i / COLS) * W;
          const x = vx + (rx - vx) * t2;
          const pulse = 0.5 + 0.5 * Math.sin(t * 0.001 + i * 0.9 + j * 1.3);
          ctx.beginPath();
          ctx.arc(x, y, 1, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(16,185,129,${0.3 * pulse})`;
          ctx.fill();
        }
      }

      // Horizontal laser scan-line
      scanY = horizon + ((t * 0.015) % (H - horizon));
      const grad = ctx.createLinearGradient(0, scanY - 6, 0, scanY + 2);
      grad.addColorStop(0, 'rgba(16,185,129,0)');
      grad.addColorStop(0.7, 'rgba(16,185,129,0.18)');
      grad.addColorStop(1, 'rgba(16,185,129,0.06)');
      ctx.fillStyle = grad;
      ctx.fillRect(0, scanY - 6, W, 8);

      // Radial vignette to hide harsh canvas edge
      const vig = ctx.createRadialGradient(W / 2, H / 2, H * 0.2, W / 2, H / 2, H * 0.85);
      vig.addColorStop(0, 'rgba(9,9,11,0)');
      vig.addColorStop(1, 'rgba(9,9,11,0.72)');
      ctx.fillStyle = vig;
      ctx.fillRect(0, 0, W, H);

      raf = requestAnimationFrame(draw);
    };

    raf = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none"
      style={{ zIndex: 0, willChange: 'transform' }}
      aria-hidden="true"
    />
  );
}
