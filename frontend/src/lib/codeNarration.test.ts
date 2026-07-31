import { containsCode, createCodeNarration, extractCodeBlocks, narrationText } from './codeNarration';

describe('code narration parser', () => {
  test('extracts Python fenced code', () => {
    const result = createCodeNarration('```python\ndef verify_state(state):\n    if not state.valid:\n        raise RuntimeError("invalid")\n```');
    expect(result.blocks).toHaveLength(1);
    expect(result.blocks[0].language).toBe('Python');
    expect(result.explanation).toContain('validation');
  });

  test('extracts JavaScript fenced code', () => {
    const blocks = extractCodeBlocks('```javascript\nfunction greet(name) { return `Hi ${name}`; }\n```');
    expect(blocks[0].language).toBe('JavaScript');
    expect(blocks[0].code).toContain('function greet');
  });

  test('extracts TypeScript fenced code', () => {
    const result = createCodeNarration('```typescript\ninterface Policy { mode: string }\nconst allow: boolean = true;\n```');
    expect(result.blocks[0].language).toBe('TypeScript');
    expect(containsCode(result.blocks[0].code)).toBe(true);
  });

  test('detects indented Python code', () => {
    expect(containsCode('    def load_state():\n        return {}')).toBe(true);
  });

  test('handles mixed prose and code', () => {
    const text = 'The loader fails closed.\n\n```python\nreturn False\n```';
    const spoken = narrationText(text, 'explain-code');
    expect(spoken).toContain('Purpose:');
    expect(spoken).not.toContain('```');
  });
});
