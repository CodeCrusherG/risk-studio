(function installPetCatalog(global) {
  "use strict";

  if (global.MarvisPetCatalog) return;

  const schemaVersion = 1;
  const defaultId = "auditbot";
  const noneId = "none";
  const storageKeys = Object.freeze({
    preference: "marvis_pet",
    explicitNone: "marvis_pet_none_explicit",
    position: "marvis_pet_position",
  });
  const aliases = Object.freeze({
    danhuang: "naitang",
    buou: "xiaojiu",
    "ragdoll-cat": "xiaojiu",
  });
  const order = Object.freeze([
    noneId,
    "naitang",
    "xiaojiu",
    defaultId,
    "auditbot-pro",
    "auditbot-poly",
    "auditbot-ink",
    "auditbot-clay",
    "auditbot-comic",
    "auditbot-pixel",
  ]);
  const definitions = Object.freeze({
    none: Object.freeze({
      name: "Hidden",
      label: "Hide companion",
      kind: "none",
      asset: null,
    }),
    naitang: Object.freeze({
      name: "Naitang",
      label: "Cream cat with blue eyes and a black bow tie.",
      kind: "spritesheet",
      asset: "static/pets/naitang/spritesheet.webp",
    }),
    xiaojiu: Object.freeze({
      name: "Xiaojiu",
      label: "Cat companion.",
      kind: "spritesheet",
      asset: "static/pets/xiaojiu/spritesheet.webp?v=c078ec6f",
    }),
    auditbot: Object.freeze({
      name: "Risk Studio",
      label: "Robot companion with blue eyes and copper headphones.",
      kind: "spritesheet",
      asset: "static/pets/auditbot/spritesheet.webp",
    }),
    "auditbot-pro": Object.freeze({
      name: "Risk Studio Pro",
      label: "3D robot companion.",
      kind: "spritesheet",
      asset: "static/pets/auditbot-pro/spritesheet.webp",
    }),
    "auditbot-poly": Object.freeze({
      name: "Risk Studio Poly",
      label: "Polygonal robot companion.",
      kind: "spritesheet",
      asset: "static/pets/auditbot-poly/spritesheet.webp",
    }),
    "auditbot-ink": Object.freeze({
      name: "Risk Studio Ink",
      label: "Line drawing of a robot.",
      kind: "spritesheet",
      asset: "static/pets/auditbot-ink/spritesheet.webp",
    }),
    "auditbot-clay": Object.freeze({
      name: "Risk Studio Clay",
      label: "Clay-style robot companion.",
      kind: "spritesheet",
      asset: "static/pets/auditbot-clay/spritesheet.webp",
    }),
    "auditbot-comic": Object.freeze({
      name: "Risk Studio Comic",
      label: "Comic-style robot companion.",
      kind: "spritesheet",
      asset: "static/pets/auditbot-comic/spritesheet.webp",
    }),
    "auditbot-pixel": Object.freeze({
      name: "Risk Studio Pixel",
      label: "Pixel-art robot companion.",
      kind: "spritesheet",
      asset: "static/pets/auditbot-pixel/spritesheet.webp",
    }),
  });

  function normalizePreference(value) {
    if (value === noneId) return noneId;
    const normalized = aliases[value] || value;
    return definitions[normalized]?.asset ? normalized : defaultId;
  }

  function resolveStoredPreference(value, explicitNone) {
    if (!value || (value === noneId && !explicitNone)) return defaultId;
    return normalizePreference(value);
  }

  function populateSelect(select, documentRef = global.document) {
    if (!select || !documentRef) return;
    const options = order.map((petId) => {
      const option = documentRef.createElement("option");
      option.value = petId;
      option.textContent = definitions[petId].name;
      return option;
    });
    select.replaceChildren(...options);
  }

  global.MarvisPetCatalog = Object.freeze({
    schemaVersion,
    defaultId,
    noneId,
    storageKeys,
    aliases,
    order,
    definitions,
    normalizePreference,
    resolveStoredPreference,
    populateSelect,
  });
})(globalThis);
