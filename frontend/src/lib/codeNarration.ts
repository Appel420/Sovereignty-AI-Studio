/**
 * Code Narration
 * Purpose: convert source-heavy assistant responses into concise, speech-friendly explanations.
 * Depends on: no external runtime services.
 * Used by: VoiceChat and future dashboard voice surfaces.
 * Security: parses text only; never executes or uploads code.
 */

export type NarrationMode = 'read' | 'explain-code' | 'summarize';

export interface CodeBlock {
  language: string;
  code: string;
}

export interface CodeNarration {
  title: string;
  purpose: string;
  inputs: string[];
  outputs: string[];
  security: string[];
  architectureRole: string;
  explanation: string;
  blocks: CodeBlock[];
}

const FENCED_CODE = /```([^\n`]*)\n?([\s\S]*?)```/g;
const LANGUAGE_NAMES: Record<string, string> = {
  js: 'JavaScript',
  javascript: 'JavaScript',
  jsx: 'JavaScript and JSX',
  ts: 'TypeScript',
  typescript: 'TypeScript',
  tsx: 'TypeScript and JSX',
  py: 'Python',
  python: 'Python',
  sh: 'shell commands',
  bash: 'shell commands',
  json: 'JSON data',
  yaml: 'YAML configuration',
  yml: 'YAML configuration',
};

function normalizeLanguage(language: string): string {
  const key = language.trim().toLowerCase();
  return LANGUAGE_NAMES[key] || (key ? language.trim() : 'source code');
}

export function extractCodeBlocks(text: string): CodeBlock[] {
  return [...text.matchAll(FENCED_CODE)]
    .map((match) => ({
      language: normalizeLanguage(match[1]),
      code: match[2].trim(),
    }))
    .filter((block) => block.code.length > 0);
}

export function containsCode(text: string): boolean {
  return extractCodeBlocks(text).length > 0 || /^ {4,}\S/m.test(text) || /\b(function|class|def|const|interface)\b/.test(text);
}

function describeBlock(block: CodeBlock): string {
  const lines = block.code.split('\n').filter((line) => line.trim());
  const functions = lines.filter((line) => /\b(def|function)\b|=>/.test(line)).length;
  const classes = lines.filter((line) => /\bclass\b/.test(line)).length;
  const checks = lines.filter((line) => /\b(if|else|try|catch|raise|throw|assert|validate)\b/.test(line)).length;
  const details: string[] = [`a ${block.language} section with ${lines.length} meaningful lines`];

  if (functions) details.push(`${functions} function or callback definition${functions === 1 ? '' : 's'}`);
  if (classes) details.push(`${classes} class definition${classes === 1 ? '' : 's'}`);
  if (checks) details.push(`${checks} visible validation or error-handling check${checks === 1 ? '' : 's'}`);

  return `The response includes ${details.join(', ')}.`;
}

export function createCodeNarration(text: string): CodeNarration {
  const blocks = extractCodeBlocks(text);
  const hasCode = containsCode(text);
  const descriptions = blocks.map(describeBlock);
  const prose = text
    .replace(FENCED_CODE, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  return {
    title: hasCode ? 'Code explanation' : 'Implementation summary',
    purpose: hasCode
      ? 'This response contains source code. The narration explains its behavior instead of reading symbols, indentation, and syntax aloud.'
      : 'This response is primarily prose, so the narration summarizes the implementation context.',
    inputs: ['The source text shown in the assistant response'],
    outputs: ['A plain-language explanation suitable for text-to-speech'],
    security: [
      'The parser inspects text only.',
      'It never executes code.',
      'The original source remains visible separately from the narration.',
    ],
    architectureRole: 'The explanation should be reviewed against the surrounding interface, policy, and data-boundary contracts.',
    explanation: [
      hasCode ? `The implementation contains ${blocks.length || 'code-like'} code section${blocks.length === 1 ? '' : 's'}.` : 'No fenced code block was found.',
      ...descriptions,
      prose ? `The surrounding context says: ${prose.slice(0, 500)}.` : '',
      'Review the purpose, inputs, outputs, security checks, and architectural role before changing the implementation.',
    ]
      .filter(Boolean)
      .join(' '),
    blocks,
  };
}

export function narrationText(text: string, mode: NarrationMode): string {
  if (mode === 'read') return text;

  const narration = createCodeNarration(text);
  if (mode === 'summarize') {
    return `${narration.title}. Purpose: ${narration.purpose} ${narration.architectureRole}`;
  }

  return [
    narration.title,
    `Purpose: ${narration.purpose}`,
    `Inputs: ${narration.inputs.join(', ')}.`,
    `Outputs: ${narration.outputs.join(', ')}.`,
    `Security: ${narration.security.join(' ')}`,
    narration.explanation,
  ].join(' ');
}
