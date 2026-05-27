/* Navbar */
export function Navbar() {
  const links = [
    { href: "#overview", label: "개요" },
    { href: "#map",      label: "위험 지도" },
    { href: "#analysis", label: "분석" },
    { href: "#features", label: "피처" },
  ];
  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <div className="navbar-logo">
          <span className="dot" />
          <span>🛴 SAFERIDE</span>
        </div>
        <ul className="navbar-links">
          {links.map(l => (
            <li key={l.href}><a href={l.href}>{l.label}</a></li>
          ))}
        </ul>
        <a
          className="btn-primary"
          style={{ padding: "8px 18px", fontSize: "0.8rem" }}
          href="https://github.com/11Won11/RoadSafe"
          target="_blank"
          rel="noreferrer"
        >
          GitHub ↗
        </a>
      </div>
    </nav>
  );
}
