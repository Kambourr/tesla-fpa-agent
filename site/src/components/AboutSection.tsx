import { profileLinks } from "../config";

const credit = "Built by Jacob Kambour, MS Finance & Analytics, Santa Clara University.";

const links = [
  { label: "GitHub", href: profileLinks.github },
  { label: "LinkedIn", href: profileLinks.linkedin },
] as const;

export function AboutSection() {
  return (
    <section className="about" aria-labelledby="about-title">
      <h2 id="about-title">About</h2>
      <p>{credit}</p>
      <ul className="about-links">
        {links.map((link) => (
          <li key={link.label}>
            <span className="about-label">{link.label}</span>
            {link.href ? (
              <a href={link.href} rel="noopener noreferrer">
                {link.label}
              </a>
            ) : (
              <span className="about-missing">Not filled in yet</span>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
