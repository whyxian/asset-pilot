"use client"

import * as React from "react"
import { createPortal } from "react-dom"

import { cn } from "@/lib/utils"

interface TooltipProps {
  content: string
  children: React.ReactNode
  className?: string
}

export function Tooltip({ content, children, className }: TooltipProps) {
  const [show, setShow] = React.useState(false)
  const triggerRef = React.useRef<HTMLDivElement>(null)
  const posRef = React.useRef({ top: 0, left: 0 })

  const handleMouseEnter = () => {
    if (triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect()
      posRef.current = { top: rect.bottom + 4, left: rect.left }
    }
    setShow(true)
  }

  const handleMouseLeave = () => setShow(false)

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
          className="fixed z-50 rounded-md bg-foreground px-2 py-1 text-xs text-background whitespace-nowrap shadow-md"
          style={{ top: posRef.current.top, left: posRef.current.left }}
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
