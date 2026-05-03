const navLinks = Array.from(document.querySelectorAll(".nav-link"));
const sections = navLinks
  .map((link) => document.querySelector(link.getAttribute("href")))
  .filter(Boolean);

const observer = new IntersectionObserver(
  (entries) => {
    const visible = entries
      .filter((entry) => entry.isIntersecting)
      .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];

    if (!visible) {
      return;
    }

    navLinks.forEach((link) => {
      link.classList.toggle("active", link.getAttribute("href") === `#${visible.target.id}`);
    });
  },
  {
    rootMargin: "-20% 0px -65% 0px",
    threshold: [0.1, 0.25, 0.5, 0.75],
  },
);

sections.forEach((section) => observer.observe(section));

const moduleSearch = document.querySelector("#module-search");
const moduleCards = Array.from(document.querySelectorAll("[data-module-card]"));
const emptyState = document.querySelector("#module-empty");

moduleSearch?.addEventListener("input", (event) => {
  const query = event.target.value.trim().toLowerCase();
  let visibleCount = 0;

  moduleCards.forEach((card) => {
    const haystack = card.textContent.toLowerCase();
    const visible = haystack.includes(query);
    card.hidden = !visible;
    if (visible) {
      visibleCount += 1;
    }
  });

  if (emptyState) {
    emptyState.hidden = visibleCount !== 0;
  }
});

document.querySelectorAll("a[href^='#']").forEach((anchor) => {
  anchor.addEventListener("click", (event) => {
    const target = document.querySelector(anchor.getAttribute("href"));
    if (!target) {
      return;
    }
    event.preventDefault();
    target.scrollIntoView({ behavior: "smooth", block: "start" });
    history.pushState(null, "", anchor.getAttribute("href"));
  });
});
