'use client';

import { useState, useEffect, useRef, useCallback, RefObject } from 'react';

export type PopoverPosition = 'right' | 'left' | 'top' | 'bottom';

interface PopoverState {
  isOpen: boolean;
  position: PopoverPosition;
  style: React.CSSProperties;
}

interface UsePopoverOptions {
  preferredPosition?: PopoverPosition;
  offset?: number;
  onClose?: () => void;
}

interface UsePopoverReturn {
  isOpen: boolean;
  position: PopoverPosition;
  style: React.CSSProperties;
  triggerRef: RefObject<HTMLButtonElement | null>;
  popoverRef: RefObject<HTMLDivElement | null>;
  open: () => void;
  close: () => void;
  toggle: () => void;
}

export function usePopover(options: UsePopoverOptions = {}): UsePopoverReturn {
  const { preferredPosition = 'right', offset = 8, onClose } = options;

  const [state, setState] = useState<PopoverState>({
    isOpen: false,
    position: preferredPosition,
    style: {},
  });

  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  // Calculate optimal position based on available space
  const calculatePosition = useCallback(() => {
    if (!triggerRef.current || !popoverRef.current) return;

    const triggerRect = triggerRef.current.getBoundingClientRect();
    const popoverRect = popoverRef.current.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    const spaceRight = viewportWidth - triggerRect.right;
    const spaceLeft = triggerRect.left;
    const spaceTop = triggerRect.top;
    const spaceBottom = viewportHeight - triggerRect.bottom;

    // Priority: right > left > bottom > top
    let position: PopoverPosition = preferredPosition;
    let style: React.CSSProperties = {};

    const popoverWidth = Math.min(popoverRect.width || 320, 320);
    const popoverHeight = popoverRect.height || 300;

    if (spaceRight >= popoverWidth + offset) {
      position = 'right';
      style = {
        left: triggerRect.right + offset,
        top: Math.max(8, Math.min(
          triggerRect.top,
          viewportHeight - popoverHeight - 8
        )),
      };
    } else if (spaceLeft >= popoverWidth + offset) {
      position = 'left';
      style = {
        left: triggerRect.left - popoverWidth - offset,
        top: Math.max(8, Math.min(
          triggerRect.top,
          viewportHeight - popoverHeight - 8
        )),
      };
    } else if (spaceBottom >= popoverHeight + offset) {
      position = 'bottom';
      style = {
        left: Math.max(8, Math.min(
          triggerRect.left,
          viewportWidth - popoverWidth - 8
        )),
        top: triggerRect.bottom + offset,
      };
    } else {
      position = 'top';
      style = {
        left: Math.max(8, Math.min(
          triggerRect.left,
          viewportWidth - popoverWidth - 8
        )),
        top: triggerRect.top - popoverHeight - offset,
      };
    }

    setState((prev) => ({
      ...prev,
      position,
      style: {
        ...style,
        position: 'fixed',
      },
    }));
  }, [preferredPosition, offset]);

  const open = useCallback(() => {
    setState((prev) => ({ ...prev, isOpen: true }));
  }, []);

  const close = useCallback(() => {
    setState((prev) => ({ ...prev, isOpen: false }));
    onClose?.();
  }, [onClose]);

  const toggle = useCallback(() => {
    if (state.isOpen) {
      close();
    } else {
      open();
    }
  }, [state.isOpen, open, close]);

  // Calculate position when opened
  useEffect(() => {
    if (state.isOpen) {
      // Use requestAnimationFrame to ensure popover is rendered
      requestAnimationFrame(() => {
        calculatePosition();
      });
    }
  }, [state.isOpen, calculatePosition]);

  // Handle outside click
  useEffect(() => {
    if (!state.isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (
        triggerRef.current &&
        !triggerRef.current.contains(target) &&
        popoverRef.current &&
        !popoverRef.current.contains(target)
      ) {
        close();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [state.isOpen, close]);

  // Handle ESC key
  useEffect(() => {
    if (!state.isOpen) return;

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        close();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [state.isOpen, close]);

  // Recalculate position on scroll/resize
  useEffect(() => {
    if (!state.isOpen) return;

    const handleReposition = () => {
      calculatePosition();
    };

    window.addEventListener('scroll', handleReposition, true);
    window.addEventListener('resize', handleReposition);

    return () => {
      window.removeEventListener('scroll', handleReposition, true);
      window.removeEventListener('resize', handleReposition);
    };
  }, [state.isOpen, calculatePosition]);

  return {
    isOpen: state.isOpen,
    position: state.position,
    style: state.style,
    triggerRef,
    popoverRef,
    open,
    close,
    toggle,
  };
}
