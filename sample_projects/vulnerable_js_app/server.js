/**
 * Vulnerable Node.js / Express Server
 * Contains documented intentional flaws:
 * 1. Dynamic code execution via eval() (JS-SEC-001)
 * 2. DOM XSS via innerHTML (JS-SEC-002)
 * 3. Prototype pollution via __proto__ (JS-SEC-006)
 * 4. SQL injection in template literal (DB-SEC-001)
 * 5. TLS verification disabled (JS-SEC-005)
 */

function handleDynamicScript(userInput) {
  // Intentional Flaw 1: eval
  return eval(userInput);
}

function renderUserProfile(container, unsanitizedBio) {
  // Intentional Flaw 2: innerHTML
  container.innerHTML = "<div>" + unsanitizedBio + "</div>";
}

function mergePayload(target, payload) {
  // Intentional Flaw 3: prototype pollution
  target.__proto__ = payload;
  return target;
}

function findUserById(db, userId) {
  // Intentional Flaw 4: Template literal SQL injection
  return db.query(`SELECT * FROM users WHERE id = ${userId}`);
}

const networkConfig = {
  // Intentional Flaw 5: Disabled TLS certificate check
  rejectUnauthorized: false
};

module.exports = {
  handleDynamicScript,
  renderUserProfile,
  mergePayload,
  findUserById,
  networkConfig
};
