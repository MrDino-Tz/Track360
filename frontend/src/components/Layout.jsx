import { useEffect, useRef, useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { api, endpoints } from '../api';
import { fmtTime } from '../format';

const NAV = [
  { to: '/', end: true, icon: 'ti ti-home', label: 'Dashboard' },
  { to: '/incidents', icon: 'ti ti-inbox', label: 'Incident Inbox' },
  { to: '/equipment', icon: 'ti ti-box-seam', label: 'Equipment' },
];

const POLL_MS = 4000;

function navClass({ isActive }) {
  return `nav-link ${isActive ? 'active' : ''}`;
}

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [clock, setClock] = useState(new Date().toLocaleString());
  const [live, setLive] = useState(true);
  const [channel, setChannel] = useState(null);
  const [flash, setFlash] = useState(false);
  const lastReceived = useRef(null);
  const flashTimer = useRef(null);

  useEffect(() => {
    const timer = setInterval(() => setClock(new Date().toLocaleString()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const data = await api.get(endpoints.channel);
        if (cancelled) return;
        setLive(true);
        setChannel(data);
        if (data.received_at && data.received_at !== lastReceived.current) {
          if (lastReceived.current !== null && !flashTimer.current) {
            setFlash(true);
            flashTimer.current = setTimeout(() => {
              flashTimer.current = null;
              if (!cancelled) setFlash(false);
            }, 4000);
          }
          lastReceived.current = data.received_at;
        }
      } catch {
        if (!cancelled) setLive(false);
      }
    }

    load();
    const timer = setInterval(load, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
      clearTimeout(flashTimer.current);
    };
  }, []);

  const badgeLive = live ? 'bg-success-subtle text-success border-success' : 'bg-danger-subtle text-danger border-danger';
  const badgeLiveText = live ? 'SMS channel live' : 'SMS channel offline';
  const badgeLiveIcon = live ? 'ti ti-message-circle' : 'ti ti-message-circle-off';

  const badgeSms = flash ? 'bg-success-subtle text-success border-success' : 'bg-primary-subtle text-primary border-primary';
  const badgeSmsText = flash
    ? 'New SMS received'
    : channel && channel.received_at
      ? `Last SMS ${fmtTime(channel.received_at)}`
      : 'Waiting for SMS';
  const badgeSmsIcon = flash ? 'ti ti-message-plus' : 'ti ti-bolt';

  const sidebarClass = `sidebar ${collapsed ? 'collapsed' : ''} ${mobileOpen ? 'mobile-show' : ''}`.trim();
  const topbarClass = `navbar bg-white border-bottom fixed-top topbar px-3 ${collapsed ? 'full' : ''}`.trim();

  return (
    <>
      <div id="overlay" className={`overlay ${mobileOpen ? 'show' : ''}`} onClick={() => setMobileOpen(false)}></div>

      <nav id="topbar" className={topbarClass}>
        <div className="d-flex align-items-center">
          <button
            type="button"
            className="d-none d-lg-inline-flex btn btn-light btn-icon btn-sm"
            onClick={() => setCollapsed((v) => !v)}
          >
            <i className="ti ti-layout-sidebar-left-expand"></i>
          </button>
          <button
            type="button"
            className="btn btn-light btn-icon btn-sm d-lg-none me-2"
            onClick={() => setMobileOpen(true)}
          >
            <i className="ti ti-layout-sidebar-left-expand"></i>
          </button>
        </div>
        <div className="d-flex align-items-center gap-3 flex-grow-1 flex-wrap">
          <span className={`badge border d-inline-flex align-items-center gap-1 ${badgeLive}`}>
            <i className={badgeLiveIcon}></i> {badgeLiveText}
          </span>
          <span className={`badge border d-inline-flex align-items-center gap-1 ${badgeSms}`}>
            <i className={badgeSmsIcon}></i> <span>{badgeSmsText}</span>
          </span>
          <span className="ms-auto text-secondary small fw-medium d-none d-md-inline">{clock}</span>
        </div>
      </nav>

      <aside id="sidebar" className={sidebarClass}>
        <div className="logo-area">
          <a href="#/" className="d-inline-flex align-items-center gap-2">
            <img src="/logo-icon.svg" alt="Track360" width="24" />
            <span className="logo-text fs-6 fw-bold text-dark">Track360</span>
          </a>
        </div>
        <ul className="nav flex-column">
          <li className="px-4 py-2">
            <small className="nav-text">Main</small>
          </li>
          {NAV.map((item) => (
            <li key={item.to}>
              <NavLink to={item.to} end={item.end} className={navClass}>
                <i className={item.icon}></i>
                <span className="nav-text">{item.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
        <div className="px-4 pt-4 pb-3 small text-secondary">
          <p className="mb-0">Phone → Africa's Talking → webhook → incident</p>
        </div>
      </aside>

      <main id="content" className={`content py-10 ${collapsed ? 'full' : ''}`.trim()}>
        <div className="container-fluid">
          <Outlet />
        </div>
      </main>
    </>
  );
}