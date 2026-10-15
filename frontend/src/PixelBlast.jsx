import { useEffect, useRef } from 'react';
import './PixelBlast.css';

export default function PixelBlast({ className = '' }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const context = canvas.getContext('2d');
    let frame;
    let width = 0;
    let height = 0;
    let dpr = 1;
    let start = performance.now();

    const resize = () => {
      const bounds = canvas.getBoundingClientRect();
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = bounds.width;
      height = bounds.height;
      canvas.width = Math.max(1, Math.floor(width * dpr));
      canvas.height = Math.max(1, Math.floor(height * dpr));
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const draw = (now) => {
      const time = (now - start) / 1000;
      context.clearRect(0, 0, width, height);
      const cell = 8;
      const columns = Math.ceil(width / cell);
      const rows = Math.ceil(height / cell);
      const centerX = width * 0.58;
      const centerY = height * 0.44;

      for (let row = 0; row < rows; row += 1) {
        for (let column = 0; column < columns; column += 1) {
          const x = column * cell + 2;
          const y = row * cell + 2;
          const distance = Math.hypot(x - centerX, (y - centerY) * 0.82);
          const cloud = Math.sin(column * 0.17 + time * 0.22) + Math.cos(row * 0.13 - time * 0.16);
          const density = Math.max(0, 1 - distance / Math.max(width, height) + cloud * 0.1);
          const shimmer = 0.78 + Math.sin(time * 1.5 + column * 0.7 + row * 0.31) * 0.16;
          const alpha = density * density * 0.18 * shimmer;
          if (alpha < 0.025) continue;
          context.fillStyle = `rgba(154, 124, 255, ${alpha})`;
          context.fillRect(x, y, 3, 3);
        }
      }
      frame = requestAnimationFrame(draw);
    };

    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    frame = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
    };
  }, []);

  return <canvas ref={canvasRef} className={`pixel-blast ${className}`} aria-hidden="true" />;
}
