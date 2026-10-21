// Kiln — kilnviewer.com: entrances, the FAQ index and the glaze test tile.

document.documentElement.classList.add("js");

// Entrance: the parts of each section rise in turn as the section arrives.
(() => {
  const items = document.querySelectorAll("[data-rise]");
  if (!("IntersectionObserver" in window)) {
    items.forEach((el) => el.classList.add("in"));
    return;
  }
  const groups = new Map();
  items.forEach((el) => {
    const group = el.closest("section, header, .cells, .about__tiles") || document.body;
    const index = groups.get(group) || 0;
    groups.set(group, index + 1);
    el.style.setProperty("--d", `${Math.min(index, 6) * 75}ms`);
  });
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("in");
          observer.unobserve(entry.target);
        }
      });
    },
    { rootMargin: "0px 0px -8% 0px" }
  );
  items.forEach((el) => observer.observe(el));

  // A fast scroll or an anchor jump can carry an element past the viewport
  // without it ever intersecting; reveal anything that is already above the fold.
  let pending = false;
  const catchUp = () => {
    pending = false;
    document.querySelectorAll("[data-rise]:not(.in)").forEach((el) => {
      if (el.getBoundingClientRect().top < window.innerHeight) {
        el.classList.add("in");
        observer.unobserve(el);
      }
    });
  };
  window.addEventListener("scroll", () => {
    if (!pending) { pending = true; requestAnimationFrame(catchUp); }
  }, { passive: true });
})();

// The glaze test tile: paint on bisque, then fire it.
(() => {
  const canvas = document.querySelector(".paint__tile");
  if (!canvas || !canvas.getContext) return;
  const ctx = canvas.getContext("2d");
  const wrap = canvas.closest(".paint");
  const swatches = [...document.querySelectorAll(".paint__glazes button")];
  const fire = document.querySelector(".paint__fire");
  const wipe = document.querySelector(".paint__clear");
  let glaze = swatches[0].dataset.glaze;

  // Bisque: warm clay with a fine speckle, drawn once with a fixed seed.
  const drawBisque = () => {
    ctx.fillStyle = "#dcc4a4";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    let seed = 7;
    const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    for (let i = 0; i < 2600; i++) {
      ctx.fillStyle = rand() > 0.5 ? "rgba(120, 86, 58, 0.18)" : "rgba(255, 244, 228, 0.22)";
      ctx.fillRect(rand() * canvas.width, rand() * canvas.height, 1.5 + rand() * 2, 1.5 + rand() * 2);
    }
    // A sample brushstroke, so the tile shows what it is for.
    paintStroke([[70, 290], [150, 250], [240, 270], [330, 230], [420, 250]], "#2bb3a6");
  };

  const dab = (x, y, colour) => {
    ctx.globalAlpha = 0.55;
    ctx.fillStyle = colour;
    ctx.beginPath();
    ctx.arc(x, y, 22, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;
  };

  const paintStroke = (points, colour) => {
    for (let i = 1; i < points.length; i++) {
      const [x0, y0] = points[i - 1];
      const [x1, y1] = points[i];
      const steps = Math.ceil(Math.hypot(x1 - x0, y1 - y0) / 6);
      for (let s = 0; s <= steps; s++) dab(x0 + ((x1 - x0) * s) / steps, y0 + ((y1 - y0) * s) / steps, colour);
    }
  };

  const toCanvas = (event) => {
    const rect = canvas.getBoundingClientRect();
    return [((event.clientX - rect.left) / rect.width) * canvas.width, ((event.clientY - rect.top) / rect.height) * canvas.height];
  };

  let last = null;
  canvas.addEventListener("pointerdown", (event) => {
    canvas.setPointerCapture(event.pointerId);
    last = toCanvas(event);
    dab(...last, glaze);
  });
  canvas.addEventListener("pointermove", (event) => {
    if (!last) return;
    const point = toCanvas(event);
    paintStroke([last, point], glaze);
    last = point;
  });
  const stop = () => { last = null; };
  canvas.addEventListener("pointerup", stop);
  canvas.addEventListener("pointercancel", stop);

  swatches.forEach((button) => {
    button.addEventListener("click", () => {
      glaze = button.dataset.glaze;
      swatches.forEach((b) => b.setAttribute("aria-checked", String(b === button)));
      wrap.classList.remove("is-fired");
      fire.textContent = "Fire it";
    });
  });

  fire.addEventListener("click", () => {
    const fired = wrap.classList.toggle("is-fired");
    fire.textContent = fired ? "Back to wet glaze" : "Fire it";
  });

  wipe.addEventListener("click", () => {
    wrap.classList.remove("is-fired");
    fire.textContent = "Fire it";
    drawBisque();
  });

  drawBisque();
})();
