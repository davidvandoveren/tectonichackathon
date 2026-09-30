import { useEffect, type RefObject } from "react";

const DRAG_THRESHOLD_PX = 6;

function horizontalScroller(target: EventTarget | null, root: HTMLElement): HTMLElement | null {
  let node = target instanceof HTMLElement ? target : null;
  while (node && node !== root) {
    const style = getComputedStyle(node);
    const scrollsX = style.overflowX === "auto" || style.overflowX === "scroll";
    if (scrollsX && node.scrollWidth > node.clientWidth + 1) return node;
    node = node.parentElement;
  }
  return null;
}

/**
 * Lets a mouse swipe horizontal lists (account cards, Kate's cards) inside `rootRef`, like a finger
 * does on a real phone. Touch and pen keep their native scrolling. A drag never triggers the click
 * on the card it started on.
 */
export function useDragToScroll(rootRef: RefObject<HTMLElement | null>): void {
  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;

    let scroller: HTMLElement | null = null;
    let startX = 0;
    let startScroll = 0;
    let dragged = false;
    let snapType = "";

    const onPointerDown = (event: PointerEvent) => {
      if (event.pointerType !== "mouse" || event.button !== 0) return;
      scroller = horizontalScroller(event.target, root);
      if (!scroller) return;
      startX = event.clientX;
      startScroll = scroller.scrollLeft;
      dragged = false;
    };

    const onPointerMove = (event: PointerEvent) => {
      if (!scroller) return;
      const delta = event.clientX - startX;
      if (!dragged && Math.abs(delta) < DRAG_THRESHOLD_PX) return;
      if (!dragged) {
        dragged = true;
        snapType = scroller.style.scrollSnapType;
        scroller.style.scrollSnapType = "none"; // follow the mouse; snap again on release
        scroller.style.cursor = "grabbing";
      }
      scroller.scrollLeft = startScroll - delta;
      event.preventDefault();
    };

    const onPointerUp = () => {
      if (scroller && dragged) {
        const target = scroller;
        target.style.cursor = "";
        target.style.scrollSnapType = snapType;
        // Snap to the nearest card, as a finger swipe would.
        target.scrollBy({ left: 0, behavior: "smooth" });
      }
      scroller = null;
    };

    const onClick = (event: MouseEvent) => {
      if (dragged) {
        event.preventDefault();
        event.stopPropagation();
        dragged = false;
      }
    };

    root.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("pointermove", onPointerMove, { passive: false });
    window.addEventListener("pointerup", onPointerUp);
    root.addEventListener("click", onClick, true);
    return () => {
      root.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      root.removeEventListener("click", onClick, true);
    };
  }, [rootRef]);
}
