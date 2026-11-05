import { useRef, type KeyboardEvent } from "react";

/**
 * Keyboard behaviour for an ARIA tablist: Left/Right (and Up/Down) move and
 * select, Home/End jump. Selection follows focus, as the pattern recommends
 * when panels render instantly.
 */
export function useTabs<T extends string>(ids: readonly T[], selected: T, onSelect: (id: T) => void) {
  const refs = useRef(new Map<T, HTMLButtonElement>());

  const onKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    const index = ids.indexOf(selected);
    let next = index;
    if (event.key === "ArrowRight" || event.key === "ArrowDown") next = (index + 1) % ids.length;
    else if (event.key === "ArrowLeft" || event.key === "ArrowUp") next = (index - 1 + ids.length) % ids.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = ids.length - 1;
    else return;
    event.preventDefault();
    onSelect(ids[next]);
    refs.current.get(ids[next])?.focus();
  };

  const tabProps = (id: T, panelId: string) => ({
    ref: (element: HTMLButtonElement | null) => {
      if (element) refs.current.set(id, element);
      else refs.current.delete(id);
    },
    role: "tab" as const,
    type: "button" as const,
    id: `${panelId}-tab-${id}`,
    "aria-selected": id === selected,
    "aria-controls": panelId,
    tabIndex: id === selected ? 0 : -1,
    onClick: () => onSelect(id),
  });

  return { onKeyDown, tabProps };
}
