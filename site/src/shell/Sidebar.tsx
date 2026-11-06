import type { RefObject } from "react";
import { MastheadMark } from "../components/MastheadMark";
import { ThemeToggle } from "../components/ThemeToggle";
import { siteName } from "../config";
import { hashForView, VIEW_IDS, VIEW_LABELS, type ViewId } from "./hashView";

type Props = {
  view: ViewId;
  open: boolean;
  onNavigate: (view: ViewId) => void;
  onClose: () => void;
  drawerRef: RefObject<HTMLElement | null>;
};

export function Sidebar({ view, open, onNavigate, onClose, drawerRef }: Props) {
  return (
    <aside
      ref={drawerRef}
      className={open ? "sidebar is-open" : "sidebar"}
      id="site-nav"
      aria-label="Site"
    >
      <div className="sidebar-brand">
        <MastheadMark />
        <p className="sidebar-name">{siteName}</p>
      </div>
      <nav className="sidebar-nav" aria-label="Views">
        {VIEW_IDS.map((id) => {
          const active = id === view;
          return (
            <a
              key={id}
              className={active ? "nav-link is-active" : "nav-link"}
              href={hashForView(id)}
              aria-current={active ? "page" : undefined}
              onClick={(event) => {
                event.preventDefault();
                onNavigate(id);
                onClose();
              }}
            >
              {VIEW_LABELS[id]}
            </a>
          );
        })}
      </nav>
      <div className="sidebar-foot">
        <ThemeToggle />
        <p className="sidebar-credit">Built by Jacob Kambour</p>
      </div>
    </aside>
  );
}
