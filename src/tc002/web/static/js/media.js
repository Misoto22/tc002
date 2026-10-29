// Where a screen's LED preview comes from: one example per screen, rendered by the server.

const EXAMPLE = { claude: "claude-busy" }; // screens whose example is not named after them

export const screenPreview = (screen) => `/api/preview/${EXAMPLE[screen] ?? screen}.gif`;
