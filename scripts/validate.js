// src/validate.js
// Thin wrapper so the schema files under src/schemas/ actually gate writes
// instead of sitting there as documentation. One compiled validator per
// entity, reused across requests (compiling per-request would be wasteful).

const Ajv = require('ajv');
const addFormats = require('ajv-formats');
const path = require('path');

const ajv = new Ajv({ allErrors: true, strict: false });
addFormats(ajv); // without this, "format": "date-time" is silently ignored (and warns on every boot)

function compile(schemaFile) {
  const schema = require(path.join(__dirname, 'schemas', schemaFile));
  return ajv.compile(schema);
}

const validators = {
  company: compile('company.schema.json'),
  provider: compile('provider.schema.json'),
  model: compile('model.schema.json'),
  api: compile('api.schema.json'),
  evidence: compile('evidence.schema.json')
};

// Schemas mark most fields required and additionalProperties:false, which is
// correct for the STORED row shape but too strict for a POST body (callers
// shouldn't have to pass created_at/updated_at, and server-assigned IDs are
// often optional). So this validates a partial view: required id-ish fields
// stay enforced via each route's own manual check; this middleware instead
// checks TYPES and ENUMS on whatever fields are present, catching e.g.
// risk_rating: "medium" (wrong case) or modalities: "TEXT" (should be array).
function validatePartial(entityName) {
  const validator = validators[entityName];
  return (req, res, next) => {
    const body = req.body || {};
    const schema = require(path.join(__dirname, 'schemas', `${entityName}.schema.json`));
    const errors = [];
    for (const [key, value] of Object.entries(body)) {
      const propSchema = schema.properties && schema.properties[key];
      if (!propSchema) continue; // unknown fields caught by route-level checks, not here
      const check = ajv.compile(propSchema);
      if (!check(value)) {
        errors.push({ field: key, errors: check.errors });
      }
    }
    if (errors.length) {
      return res.status(400).json({ error: 'schema_validation_failed', details: errors });
    }
    next();
  };
}

module.exports = { validatePartial };
