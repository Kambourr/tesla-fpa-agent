import { useEffect, useId, useRef, useState, type RefObject } from "react";
import { createPortal } from "react-dom";
import { type QuarterRecord } from "../quarters";

type QuarterPickerProps = {
  quarters: readonly QuarterRecord[];
  selectedId: string;
  onSelect: (id: string) => void;
  menuRoot: RefObject<HTMLDivElement | null>;
};

export function QuarterPicker({ quarters, selectedId, onSelect, menuRoot }: QuarterPickerProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const listId = useId();
  const selected = quarters.find((quarter) => quarter.id === selectedId) ?? quarters[0];

  useEffect(() => {
    if (!open) {
      return;
    }
    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Node;
      if (rootRef.current?.contains(target) || listRef.current?.contains(target)) {
        return;
      }
      setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  useEffect(() => {
    if (!open) {
      return;
    }
    const current = listRef.current?.querySelector<HTMLButtonElement>('[aria-selected="true"]');
    current?.focus();
  }, [open]);

  if (!selected) {
    return null;
  }

  const focusOption = (index: number) => {
    const options = listRef.current?.querySelectorAll<HTMLButtonElement>('[role="option"]');
    if (!options || options.length === 0) {
      return;
    }
    const next = (index + options.length) % options.length;
    options[next]?.focus();
  };

  const indexOfFocus = () => {
    const options = [
      ...(listRef.current?.querySelectorAll<HTMLButtonElement>('[role="option"]') ?? []),
    ];
    return options.findIndex((option) => option === document.activeElement);
  };

  const menu =
    open && menuRoot.current
      ? createPortal(
          <ul
            ref={listRef}
            id={listId}
            className="quarter-menu"
            role="listbox"
            aria-label="Quarter"
            tabIndex={-1}
          >
            {quarters.map((quarter) => {
              const isSelected = quarter.id === selected.id;
              return (
                <li key={quarter.id} role="presentation">
                  <button
                    type="button"
                    role="option"
                    className="quarter-option"
                    tabIndex={-1}
                    aria-selected={isSelected}
                    onClick={() => {
                      onSelect(quarter.id);
                      setOpen(false);
                      buttonRef.current?.focus();
                    }}
                    onKeyDown={(event) => {
                      if (event.key === "ArrowDown") {
                        event.preventDefault();
                        focusOption(indexOfFocus() + 1);
                      } else if (event.key === "ArrowUp") {
                        event.preventDefault();
                        focusOption(indexOfFocus() - 1);
                      } else if (event.key === "Home") {
                        event.preventDefault();
                        focusOption(0);
                      } else if (event.key === "End") {
                        event.preventDefault();
                        focusOption(-1);
                      } else if (event.key === "Escape") {
                        event.preventDefault();
                        setOpen(false);
                        buttonRef.current?.focus();
                      }
                    }}
                  >
                    <OptionTick selected={isSelected} />
                    <span>{quarter.label}</span>
                    {isSelected ? <span className="visually-hidden">Selected</span> : null}
                  </button>
                </li>
              );
            })}
          </ul>,
          menuRoot.current,
        )
      : null;

  return (
    <div className="quarter-picker" ref={rootRef}>
      <button
        ref={buttonRef}
        type="button"
        className="quarter-button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        aria-label={`Quarter ${selected.label}`}
        onClick={() => setOpen((value) => !value)}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            setOpen(true);
          }
        }}
      >
        <span className="quarter-kicker">Quarter</span>
        <span className="quarter-value">{selected.label}</span>
        <Caret expanded={open} />
      </button>
      {menu}
    </div>
  );
}

function Caret({ expanded }: { expanded: boolean }) {
  return (
    <svg
      className={expanded ? "quarter-caret is-open" : "quarter-caret"}
      viewBox="0 0 12 8"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M1 1.5 L6 6.5 L11 1.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    </svg>
  );
}

function OptionTick({ selected }: { selected: boolean }) {
  return (
    <svg className="option-tick" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      {selected ? (
        <path
          d="M3 8.2c1 .8 1.8 2 2.5 3.2C7.4 8 9.4 5.4 13 3.2"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
        />
      ) : null}
    </svg>
  );
}
