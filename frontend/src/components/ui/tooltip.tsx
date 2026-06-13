"use client"

import * as React from "react"
import { createPortal } from "react-dom"

import { cn } from "@/lib/utils"

interface TooltipProps {
  content: string
  children: React.ReactNode
  className?: string
}

const VIEWPORT_PADDING = 8 // tooltip 与屏幕边缘的最小留白

export function Tooltip({ content, children, className }: TooltipProps) {
  const [show, setShow] = React.useState(false)
  const [pos, setPos] = React.useState({ top: 0, left: 0 })
  const triggerRef = React.useRef<HTMLDivElement>(null)
  const tooltipRef = React.useRef<HTMLDivElement>(null)

  const handleMouseEnter = () => {
    if (triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect()
      setPos({ top: rect.bottom + 4, left: rect.left })
    }
    setShow(true)
  }

  const handleMouseLeave = () => setShow(false)

  // tooltip 渲染后测量宽度，若超出屏幕右边界则向左夹紧
  React.useLayoutEffect(() => {
    if (!show || !tooltipRef.current) return
    const tooltipWidth = tooltipRef.current.offsetWidth
    const maxLeft = window.innerWidth - tooltipWidth - VIEWPORT_PADDING
    if (pos.left > maxLeft) {
      setPos((prev) => ({ ...prev, left: Math.max(VIEWPORT_PADDING, maxLeft) }))
    }
  }, [show, pos.left])

  return (
    <>
      <div
        ref={triggerRef}
        className={cn("relative inline-flex", className)}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {children}
      </div>
      {show && createPortal(
        <div
          ref={tooltipRef}
          className="fixed z-50 rounded-md bg-foreground px-2 py-1 text-xs text-background whitespace-nowrap shadow-md"
          style={{ top: pos.top, left: pos.left }}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        >
          {content}
        </div>,
        document.body,
      )}
    </>
  )
}
