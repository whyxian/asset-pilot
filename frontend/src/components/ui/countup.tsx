import { useEffect, useState, useRef } from 'react'

interface CountUpProps {
  end: number
  duration?: number
  decimals?: number
  formattingFn?: (v: number) => string
}

/**
 * 数字滚动动画组件
 * 从 0 到 end 做 ease-out cubic 过渡
 */
export function CountUp({ end, duration = 0.8, formattingFn }: CountUpProps) {
  const [count, setCount] = useState(0)
  const startTimeRef = useRef<number | null>(null)
  const rafRef = useRef<number>(0)

  useEffect(() => {
    startTimeRef.current = null
    setCount(0)

    const animate = (timestamp: number) => {
      if (startTimeRef.current === null) startTimeRef.current = timestamp
      const elapsed = timestamp - startTimeRef.current
      const progress = Math.min(elapsed / (duration * 1000), 1)
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3)
      setCount(end * eased)

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate)
      } else {
        setCount(end)
      }
    }

    rafRef.current = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(rafRef.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [end, duration])

  if (formattingFn) return <>{formattingFn(count)}</>
  return <>{count.toFixed(2)}</>
}
