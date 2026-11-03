// Entry of src/static/js/schema-form.min.js, exposed as the SchemaForm global.
import { createRef, useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { getDefaultRegistry, withTheme } from '@rjsf/core';
import { Theme } from '@rjsf/react-bootstrap';
import {
  TranslatableString, englishStringTranslator, getUiOptions, replaceStringParameters
} from '@rjsf/utils';
import { customizeValidator } from '@rjsf/validator-ajv8';
import Accordion from 'react-bootstrap/Accordion';
import localizeCa from 'ajv-i18n/localize/ca';
import localizeDe from 'ajv-i18n/localize/de';
import localizeEs from 'ajv-i18n/localize/es';
import localizeFr from 'ajv-i18n/localize/fr';

const Form = withTheme(Theme);
const DefaultObjectField = getDefaultRegistry().fields.ObjectField;
const ThemeObjectFieldTemplate = Theme.templates.ObjectFieldTemplate;

const LOCALIZERS = { ca: localizeCa, de: localizeDe, es: localizeEs, fr: localizeFr };

// Ace editor options of the JSON fields, also used by the page for its own JSON editors
export const ACE_OPTIONS = {
  mode: 'ace/mode/json', fontSize: 14, tabSize: 2, wrap: true, showGutter: false, showPrintMargin: false
};

const invalidJsonMessage = (translations) => translations.InvalidJson || 'Invalid JSON';

// TranslatableString values are the English strings, translations are keyed by enum name
const TRANSLATABLE_NAMES = Object.fromEntries(
  Object.entries(TranslatableString).map(([name, value]) => [value, name])
);

function stringTranslator(translations) {
  return (stringToTranslate, params) => {
    const translated = translations[TRANSLATABLE_NAMES[stringToTranslate]];
    return translated
      ? replaceStringParameters(translated, params)
      : englishStringTranslator(stringToTranslate, params);
  };
}

// Object template grouping the properties in collapsible sections, as listed in the
// "sections" ui option ([{title, fields: [...], expanded}]). Properties listed in no
// section are shown above the sections.
function SectionsObjectFieldTemplate(props) {
  const { sections } = getUiOptions(props.uiSchema);
  if (!sections) {
    return <ThemeObjectFieldTemplate {...props} />;
  }
  const byName = Object.fromEntries(props.properties.map((p) => [p.name, p]));
  const sectioned = new Set(sections.flatMap((section) => section.fields));
  const renderProperty = (property) => property && (
    <div key={property.name} className={property.hidden ? 'd-none' : 'mb-3'}>{property.content}</div>
  );
  const expanded = sections.map((section, idx) => section.expanded && String(idx)).filter(Boolean);
  return (
    <>
      {props.properties.filter((p) => !sectioned.has(p.name)).map(renderProperty)}
      <Accordion defaultActiveKey={expanded} alwaysOpen className="mb-3">
        {sections.map((section, idx) => (
          <Accordion.Item key={idx} eventKey={String(idx)}>
            <Accordion.Header>{section.title}</Accordion.Header>
            <Accordion.Body>{section.fields.map((name) => renderProperty(byName[name]))}</Accordion.Body>
          </Accordion.Item>
        ))}
      </Accordion>
    </>
  );
}

// Field editing a free-form value as JSON text, with the Ace editor when loaded.
// Fields holding invalid JSON are listed in formContext.invalidJson, so that the
// form validation fails instead of submitting their last valid value.
function JsonField({ formData, onChange, fieldPathId, name, schema, uiSchema, registry }) {
  const [text, setText] = useState(() => (formData === undefined ? '' : JSON.stringify(formData, null, 2)));
  const [invalid, setInvalid] = useState(false);
  const editorRef = useRef(null);
  const { translations = {}, invalidJson } = registry.formContext;
  const label = getUiOptions(uiSchema).title ?? schema.title ?? name;
  const pathKey = JSON.stringify(fieldPathId.path);

  const setValidity = (valid) => {
    setInvalid(!valid);
    if (valid) {
      invalidJson.delete(pathKey);
    } else {
      invalidJson.set(pathKey, { path: fieldPathId.path, label });
    }
  };
  const update = (value) => {
    setText(value);
    if (value.trim() === '') {
      setValidity(true);
      onChange(undefined, fieldPathId.path);
      return;
    }
    try {
      const parsed = JSON.parse(value);
      setValidity(true);
      onChange(parsed, fieldPathId.path);
    } catch (e) {
      setValidity(false);
    }
  };
  // the editor calls the update of the latest render
  const updateRef = useRef(update);
  updateRef.current = update;

  useEffect(() => {
    if (!window.ace || !editorRef.current) {
      return () => invalidJson.delete(pathKey);
    }
    const editor = window.ace.edit(editorRef.current, { ...ACE_OPTIONS, minLines: 3, maxLines: 20, value: text });
    editor.session.on('change', () => updateRef.current(editor.getValue()));
    return () => {
      editor.destroy();
      invalidJson.delete(pathKey);
    };
  }, []);

  const { DescriptionFieldTemplate } = registry.templates;
  return (
    <div className="mb-0">
      <label className="form-label" htmlFor={fieldPathId.$id}>{label}</label>
      {window.ace ? (
        <div ref={editorRef} id={fieldPathId.$id} className="border rounded" />
      ) : (
        <textarea
          id={fieldPathId.$id} className="form-control font-monospace" rows={5}
          value={text} onChange={(ev) => update(ev.target.value)}
        />
      )}
      {invalid && <div className="invalid-feedback d-block">{invalidJsonMessage(translations)}</div>}
      {schema.description && (
        <DescriptionFieldTemplate
          id={`${fieldPathId.$id}__description`} description={schema.description}
          schema={schema} uiSchema={uiSchema} registry={registry}
        />
      )}
    </div>
  );
}

// Object schemas without any property definition, edited as JSON since the default
// object field only shows the defined properties
const FREE_FORM_EXCLUDED_KEYWORDS = ['properties', 'additionalProperties', 'patternProperties', 'allOf', 'anyOf', 'oneOf'];
function isFreeFormObject(schema) {
  return FREE_FORM_EXCLUDED_KEYWORDS.every((keyword) => (
    schema[keyword] === undefined || (keyword === 'properties' && Object.keys(schema.properties).length === 0)
  ));
}

function ObjectField(props) {
  return isFreeFormObject(props.schema) ? <JsonField {...props} /> : <DefaultObjectField {...props} />;
}

/**
 * Render a form for the schema in the container element, return a handle whose
 * submit() validates the form and calls onSubmit if it is valid.
 *
 * options: schema, uiSchema, formData, locale, translations (RJSF interface strings
 * keyed by TranslatableString name, and InvalidJson), onSubmit(formData)
 */
export function render(container, options) {
  const validator = customizeValidator({}, LOCALIZERS[options.locale]);
  const formRef = createRef();
  const translations = options.translations || {};
  const invalidJson = new Map();
  const customValidate = (formData, errors) => {
    const message = invalidJsonMessage(translations);
    invalidJson.forEach(({ path, label }) => {
      const fieldErrors = path.reduce((node, part) => node && node[part], errors);
      if (fieldErrors) {
        fieldErrors.addError(message);
      } else {
        errors.addError(`${label}: ${message}`);
      }
    });
    return errors;
  };
  createRoot(container).render(
    <Form
      ref={formRef}
      schema={options.schema}
      uiSchema={options.uiSchema || {}}
      formData={options.formData}
      validator={validator}
      translateString={stringTranslator(translations)}
      formContext={{ translations, invalidJson }}
      customValidate={customValidate}
      templates={{ ObjectFieldTemplate: SectionsObjectFieldTemplate }}
      fields={{ json: JsonField, ObjectField }}
      experimental_defaultFormStateBehavior={{ emptyObjectFields: 'skipDefaults' }}
      noHtml5Validate
      onSubmit={({ formData }) => options.onSubmit && options.onSubmit(formData)}
    />
  );
  return { submit: () => formRef.current.submit() };
}
